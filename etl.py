import configparser
from datetime import datetime
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col
from pyspark.sql.functions import year, month, dayofmonth, hour, weekofyear, date_format

# ToDo: probs need this: .dropDuplicates()


# set config file
config = configparser.ConfigParser()
config.read('dl.cfg')


# get AWS access and secrete keys
os.environ['AWS_ACCESS_KEY_ID']=config['KEY']['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY']=config['KEY']['AWS_SECRET_ACCESS_KEY']


def create_spark_session():
    spark = SparkSession \
        .builder \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:2.7.0") \
        .getOrCreate()
    return spark


def process_song_data(spark, input_data, output_data):
    # get filepath to song data file
    song_data = os.path.join(input_data, "song_data/*/*/*/*.json")
    
    # read song data file
    df = spark.read.json(song_data)

    # extract columns to create songs table
    songs_table = df['song_id', 'title', 'artist_id', 'year',  'duration']
    
    # write songs table to parquet files partitioned by year and artist
    songs_table.write.partitionBy('year', 'artist_id').parquet(os.path.join(output_data, 'songs'), 'overwrite')

    # extract columns to create artists table
    artists_table = df['artist_id', 'artist_name', 'artist_location', 'artist_latitude', 'artist_longitude']
    
    # write artists table to parquet files
    artists_table.write.parquet(os.path.join(output_data, 'artist'), 'overwrite')


def process_log_data(spark, input_data, output_data):
    # get filepath to log data file
    log_data = os.path.join(input_data, "log_data/*/*/*/*.json")

    # read log data file
    df = spark.read.json(log_data) 
    
    # filter by actions for song plays
    df = df[df.page == 'NextSong']

    # extract columns for users table
    users_table = df.select(col('userId').alias('user_id'),
                            col('firstName').alias('first_name'),
                            col('lastName').alias('last_name'),
                            'gender',
                            'level')
    
    # write users table to parquet files     
    users_table.write.parquet(os.path.join(output_data, 'users'), 'overwrite')
        
    # create timestamp column from original timestamp column
    get_timestamp = udf(lambda x: str(int(int(x) / 1000)))
    df = df.withColumn("timestamp", get_timestamp(df.ts))    
        
    # create datetime column from original timestamp column
    get_datetime = udf(lambda x: str(datetime.fromtimestamp(int(x) / 1000.0)))
    df = df.withColumn("datetime", get_datetime(df.ts))
    
    # extract columns to create time table
    time_table = df.select('ts',
                           'timestamp', 
                           hour('datetime').alias('hour'),
                           dayofmonth('datetime').alias('day'),
                           weekofyear('datetime').alias('week'),
                           month('datetime').alias('month'),
                           year('datetime').alias('year'),
                           date_format('datetime', 'F').alias('weekday'))
        
    # write time table to parquet files partitioned by year and month
    time_table.write.partitionBy('year', 'month').parquet(os.path.join(output_data, 'time'), 'overwrite')

    # read song data file
    song_df = spark.read.json(os.path.join(input_data, "song_data/A/A/A/TRAAAAK128F9318786.json"))

    # extract columns from joined song and log datasets to create songplays table 
    songplays_table = (df.join(song_df, (df.song == song_df.title) 
                                      & (df.artist == song_df.artist_name)
                                      & (df.length == song_df.duration), 'left_outer')
                         .select(df.timestamp,
                                 col('userId').alias('user_id'),
                                 df.level,
                                 song_df.song_id,
                                 song_df.artist_id,
                                 col('sessionId').alias('session_id'),
                                 df.location,
                                 col('useragent').alias('user_agent'),
                                 year('datetime').alias('year'),
                                 month('datetime').alias('month')))                                                                

    # write songplays table to parquet files partitioned by year and month
    songplays_table.write.partitionBy('year', 'month').parquet(os.path.join(output_data, 'songplays'), 'overwrite')


def main():
    spark = create_spark_session()
    input_data = "s3a://udacity-dend/"
    output_data = "s3a://dan-data-lake/analytics/"
    
    process_song_data(spark, input_data, output_data)    
    process_log_data(spark, input_data, output_data)


if __name__ == "__main__":
    main()
