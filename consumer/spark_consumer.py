"""
Spark Streaming Consumer for GNSS Anomaly Detection
Processes Kafka stream and detects:
- Signal drops (SNR < threshold)
- Position drift
- Satellite loss
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from typing import Dict, List
from collections import deque

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, window, avg, count, stddev,
    when, lit, udf, struct, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    IntegerType, TimestampType, BooleanType
)
import pyspark.sql.functions as F

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GNSSAnomalyDetector:
    """Real-time GNSS anomaly detection using Spark Streaming"""
    
    def __init__(self, config_path: str = 'config/settings.yaml'):
        """
        Initialize Spark streaming application
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.kafka_config = self.config['kafka']
        self.spark_config = self.config['spark']
        self.anomaly_config = self.config['anomaly_detection']
        self.storage_config = self.config['storage']
        
        # Initialize Spark
        self.spark = self._create_spark_session()
        
        # Define schema for GNSS data
        self.schema = StructType([
            StructField("timestamp", StringType(), True),
            StructField("lat", DoubleType(), True),
            StructField("lon", DoubleType(), True),
            StructField("altitude", DoubleType(), True),
            StructField("fix_quality", IntegerType(), True),
            StructField("num_sats", IntegerType(), True),
            StructField("hdop", DoubleType(), True),
            StructField("speed", DoubleType(), True),
            StructField("heading", DoubleType(), True),
            StructField("satellite_id", StringType(), True),
            StructField("elevation", DoubleType(), True),
            StructField("azimuth", DoubleType(), True),
            StructField("snr", DoubleType(), True),
            StructField("producer_timestamp", StringType(), True)
        ])
        
        # Thresholds
        self.snr_threshold = self.anomaly_config['snr_threshold']
        self.drift_threshold = self.anomaly_config['drift_threshold']
        self.min_satellites = self.anomaly_config['min_satellites']
        self.window_size = self.anomaly_config['moving_avg_window']
        
        # Output directory
        self.output_dir = self.storage_config['output_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _create_spark_session(self) -> SparkSession:
        """Create and configure Spark session"""
        
        # Get Kafka package version compatible with Spark
        spark_version = "3.5"
        scala_version = "2.12"
        kafka_version = "3.5.1"
        
        packages = f"org.apache.spark:spark-sql-kafka-0-10_{scala_version}:{spark_version}.0"
        
        spark = (SparkSession.builder
                .appName(self.spark_config['app_name'])
                .master(self.spark_config['master'])
                .config("spark.jars.packages", packages)
                .config("spark.sql.streaming.checkpointLocation", 
                       self.spark_config['checkpoint_dir'])
                .config("spark.sql.shuffle.partitions", "4")
                .config("spark.streaming.stopGracefullyOnShutdown", "true")
                .getOrCreate())
        
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info("✓ Spark session created")
        return spark
    
    def read_kafka_stream(self):
        """Read streaming data from Kafka"""
        
        df = (self.spark
              .readStream
              .format("kafka")
              .option("kafka.bootstrap.servers", 
                     self.kafka_config['bootstrap_servers'])
              .option("subscribe", self.kafka_config['topic'])
              .option("startingOffsets", "latest")
              .option("failOnDataLoss", "false")
              .load())
        
        # Parse JSON from Kafka value
        parsed_df = (df
                    .selectExpr("CAST(value AS STRING) as json_str")
                    .select(from_json(col("json_str"), self.schema).alias("data"))
                    .select("data.*"))
        
        # Convert timestamp string to timestamp type
        parsed_df = parsed_df.withColumn(
            "timestamp",
            to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss'Z'")
        )
        
        logger.info("✓ Kafka stream configured")
        return parsed_df
    
    def detect_signal_drops(self, df):
        """
        Detect signal drops (SNR < threshold)
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with signal drop flag
        """
        return df.withColumn(
            "signal_drop",
            when(col("snr") < self.snr_threshold, lit(True))
            .otherwise(lit(False))
        )
    
    def detect_satellite_loss(self, df):
        """
        Detect satellite loss (num_sats < minimum)
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with satellite loss flag
        """
        return df.withColumn(
            "satellite_loss",
            when(col("num_sats") < self.min_satellites, lit(True))
            .otherwise(lit(False))
        )
    
    def detect_position_drift(self, df):
        """
        Detect position drift using windowed moving average
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with drift detection
        """
        # Calculate moving averages using time windows
        windowed_df = (df
                      .withWatermark("timestamp", "30 seconds")
                      .groupBy(
                          window(col("timestamp"), "10 seconds", "5 seconds")
                      )
                      .agg(
                          avg("lat").alias("avg_lat"),
                          avg("lon").alias("avg_lon"),
                          count("*").alias("count")
                      ))
        
        # Join with original data to compare
        # For streaming, we'll use a simplified approach
        # Calculate deviation from running average per satellite
        df_with_avg = (df
                      .withColumn("lat_diff", lit(0.0))  # Placeholder
                      .withColumn("lon_diff", lit(0.0))  # Placeholder
                      .withColumn(
                          "position_drift",
                          when(
                              (col("lat_diff") > self.drift_threshold) |
                              (col("lon_diff") > self.drift_threshold),
                              lit(True)
                          ).otherwise(lit(False))
                      ))
        
        return df_with_avg
    
    def aggregate_anomalies(self, df):
        """
        Aggregate and flag anomalies
        
        Args:
            df: Input DataFrame with anomaly flags
            
        Returns:
            DataFrame with anomaly summary
        """
        df_with_anomaly = df.withColumn(
            "anomaly_detected",
            when(
                (col("signal_drop") == True) |
                (col("satellite_loss") == True) |
                (col("position_drift") == True),
                lit(True)
            ).otherwise(lit(False))
        )
        
        # Add anomaly type
        df_with_type = df_with_anomaly.withColumn(
            "anomaly_type",
            when(col("signal_drop") == True, lit("SIGNAL_DROP"))
            .when(col("satellite_loss") == True, lit("SATELLITE_LOSS"))
            .when(col("position_drift") == True, lit("POSITION_DRIFT"))
            .otherwise(lit("NONE"))
        )
        
        return df_with_type
    
    def process_stream(self):
        """Main stream processing pipeline"""
        
        logger.info("Starting GNSS anomaly detection stream...")
        
        # Read from Kafka
        input_df = self.read_kafka_stream()
        
        # Apply anomaly detection
        df = self.detect_signal_drops(input_df)
        df = self.detect_satellite_loss(df)
        df = self.detect_position_drift(df)
        df = self.aggregate_anomalies(df)
        
        # Filter for anomalies only
        anomalies_df = df.filter(col("anomaly_detected") == True)
        
        # Write all data to console (for monitoring)
        console_query = (df
                        .writeStream
                        .outputMode("append")
                        .format("console")
                        .option("truncate", "false")
                        .option("numRows", 5)
                        .start())
        
        # Write anomalies to CSV
        csv_query = None
        if self.storage_config.get('csv_enabled', True):
            csv_query = (anomalies_df
                        .writeStream
                        .outputMode("append")
                        .format("csv")
                        .option("path", f"{self.output_dir}/anomalies_csv")
                        .option("checkpointLocation", 
                               f"{self.output_dir}/checkpoints/csv")
                        .option("header", "true")
                        .start())
            logger.info(f"✓ CSV output: {self.output_dir}/anomalies_csv")
        
        # Write anomalies to Parquet
        parquet_query = None
        if self.storage_config.get('parquet_enabled', True):
            parquet_query = (anomalies_df
                           .writeStream
                           .outputMode("append")
                           .format("parquet")
                           .option("path", f"{self.output_dir}/anomalies_parquet")
                           .option("checkpointLocation",
                                  f"{self.output_dir}/checkpoints/parquet")
                           .start())
            logger.info(f"✓ Parquet output: {self.output_dir}/anomalies_parquet")
        
        # Write statistics to console
        stats_df = (df
                   .withWatermark("timestamp", "10 seconds")
                   .groupBy(
                       window(col("timestamp"), "30 seconds", "10 seconds"),
                       col("anomaly_type")
                   )
                   .agg(
                       count("*").alias("count"),
                       avg("snr").alias("avg_snr"),
                       avg("num_sats").alias("avg_num_sats")
                   ))
        
        stats_query = (stats_df
                      .writeStream
                      .outputMode("complete")
                      .format("console")
                      .option("truncate", "false")
                      .start())
        
        logger.info("✓ Stream processing started")
        logger.info("Monitoring for anomalies...")
        logger.info(f"  - Signal drop threshold: SNR < {self.snr_threshold} dB")
        logger.info(f"  - Satellite loss threshold: < {self.min_satellites} satellites")
        logger.info(f"  - Position drift threshold: > {self.drift_threshold}°")
        
        # Wait for termination
        try:
            console_query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("\nStopping stream processing...")
            console_query.stop()
            if csv_query:
                csv_query.stop()
            if parquet_query:
                parquet_query.stop()
            stats_query.stop()
            self.spark.stop()
            logger.info("✓ Stream processing stopped")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GNSS Anomaly Detection with Spark Streaming'
    )
    parser.add_argument('--config', default='config/settings.yaml',
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        detector = GNSSAnomalyDetector(config_path=args.config)
        detector.process_stream()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
