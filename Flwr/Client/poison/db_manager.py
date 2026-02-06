
import mysql.connector
from mysql.connector import errorcode
import json
import time

class DBManager:
    """
    负责管理本地 MySQL 数据库连接和初始化
    
    Database: tmaa_simulation
    Tables:
        - device_profiles: 静态设备画像
        - telemetry_logs: 动态运行时遥测
    """
    
    def __init__(self, host="127.0.0.1", port=3306, user="root", password="root123456"):
        self.config = {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'raise_on_warnings': False
        }
        self.db_name = "tmaa_simulation"
        self._init_db()

    def _init_db(self):
        """初始化数据库和表结构"""
        try:
            # 1. 连接 MySQL Server (不指定 DB)
            cnx = mysql.connector.connect(**self.config)
            cursor = cnx.cursor()
            
            # 2. 创建 Database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
            cnx.database = self.db_name
            
            # 3. 创建 device_profiles 表 (静态画像)
            # 存储设备的硬性指标
            table_profiles = """
            CREATE TABLE IF NOT EXISTS device_profiles (
                device_id VARCHAR(50) PRIMARY KEY,
                hardware_type VARCHAR(50),
                cpu_cores INT,
                total_memory_gb FLOAT,
                tflops FLOAT,
                tee_type VARCHAR(20),
                is_malicious BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """
            cursor.execute(table_profiles)
            
            # 4. 创建 telemetry_logs 表 (运行时遥测)
            # 存储时序数据，使用 PARTITION 可以优化，这里暂简易实现
            table_logs = """
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id VARCHAR(50),
                timestamp DOUBLE,
                phase VARCHAR(20),
                cpu_usage FLOAT,
                memory_usage_mb FLOAT,
                gpu_util FLOAT,
                temperature_c FLOAT,
                fan_speed_rpm INT,
                latency_ms FLOAT,
                FOREIGN KEY (device_id) REFERENCES device_profiles(device_id),
                INDEX idx_dev_time (device_id, timestamp)
            ) ENGINE=InnoDB;
            """
            cursor.execute(table_logs)
            
            cnx.commit()
            cursor.close()
            cnx.close()
            print(f"✅ [DBManager] Database '{self.db_name}' initialized successfully.")
            
        except mysql.connector.Error as err:
            print(f"❌ [DBManager] Failed to init DB: {err}")
            raise

    def get_connection(self):
        """获取数据库连接"""
        config = self.config.copy()
        config['database'] = self.db_name
        return mysql.connector.connect(**config)

    def register_device(self, profile: dict):
        """注册或更新设备画像"""
        cnx = self.get_connection()
        cursor = cnx.cursor()
        
        sql = """
        INSERT INTO device_profiles 
        (device_id, hardware_type, cpu_cores, total_memory_gb, tflops, tee_type, is_malicious)
        VALUES (%(device_id)s, %(hardware_type)s, %(cpu_cores)s, %(total_memory_gb)s, %(tflops)s, %(tee_type)s, %(is_malicious)s)
        AS new_val
        ON DUPLICATE KEY UPDATE
        hardware_type=new_val.hardware_type, 
        cpu_cores=new_val.cpu_cores,
        total_memory_gb=new_val.total_memory_gb,
        tflops=new_val.tflops,
        tee_type=new_val.tee_type,
        is_malicious=new_val.is_malicious
        """
        try:
            cursor.execute(sql, profile)
            cnx.commit()
        except mysql.connector.Error as err:
            print(f"Error registering device: {err}")
        finally:
            cursor.close()
            cnx.close()

    def insert_telemetry_batch(self, logs: list):
        """批量插入遥测数据"""
        if not logs:
            return
            
        cnx = self.get_connection()
        cursor = cnx.cursor()
        
        sql = """
        INSERT INTO telemetry_logs 
        (device_id, timestamp, phase, cpu_usage, memory_usage_mb, gpu_util, temperature_c, fan_speed_rpm, latency_ms)
        VALUES (%(device_id)s, %(timestamp)s, %(phase)s, %(cpu_usage)s, %(memory_usage_mb)s, %(gpu_util)s, %(temperature_c)s, %(fan_speed_rpm)s, %(latency_ms)s)
        """
        try:
            cursor.executemany(sql, logs)
            cnx.commit()
            print(f"    💾 Saved {len(logs)} telemetry records to DB.")
        except mysql.connector.Error as err:
            print(f"Error inserting logs: {err}")
        finally:
            cursor.close()
            cnx.close()
