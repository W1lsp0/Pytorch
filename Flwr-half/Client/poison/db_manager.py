"""
==============================================================================
💾 Database Manager 数据库管理模块
==============================================================================
本模块负责管理仿真环境的 MySQL 数据库连接、初始化及数据操作。

主要功能:
    1. 数据库自动初始化 (建库、建表)
    2. 静态设备画像存储 (Device Profiles)
    3. 动态遥测日志存储 (Telemetry Logs)
    4. 高效的批量数据写入

Schema 设计:
    - device_profiles: 存储设备不可变的硬件属性
    - telemetry_logs: 存储随时间变化的时序遥测数据 (支持分区优化)

作者: Flwr 联邦学习项目
==============================================================================
"""

import mysql.connector
from mysql.connector import errorcode
import json
import time
from typing import List, Dict, Optional, Any

class DBManager:
    """
    负责管理本地 MySQL 数据库连接和初始化

    Database: tmaa_simulation
    Tables:
        - device_profiles: 静态设备画像
        - telemetry_logs: 动态运行时遥测
    """

    def __init__(self, host="202.113.76.179", port=3306, user="root", password="root123456"):
        """
        初始化数据库管理器
        
        Args:
            host (str): MySQL 主机地址 (默认 127.0.0.1)
            port (int): MySQL 端口
            user (str): 用户名
            password (str): 密码
        """
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
        """
        初始化数据库和表结构
        
        如果数据库不存在则创建；如果表不存在则创建。
        自动处理分区表的创建逻辑。
        """
        # 收集所有初始化信息，最后一次性输出
        _init_lines = [
            f"┌{'─'*58}┐",
            f"│  🔌 正在连接 MySQL: {self.config['host']}:{self.config['port']}...{' '*19}│",
        ]
        
        try:
            # 1. 连接 MySQL Server (不指定 DB)
            cnx = mysql.connector.connect(**self.config)
            cursor = cnx.cursor()

            # 2. 创建 Database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name}")
            cnx.database = self.db_name
            
            _init_lines.append(f"│  ✅ 数据库 '{self.db_name}' 准备就绪{' '*26}│")

            # 3. 创建 device_profiles 表 (静态画像)
            # 存储设备的硬性指标
            table_profiles = """
            CREATE TABLE IF NOT EXISTS device_profiles (
                device_id VARCHAR(50) PRIMARY KEY COMMENT '设备唯一ID',
                hardware_type VARCHAR(50) COMMENT '硬件型号 (如 RTX3090)',
                attack_type VARCHAR(50) DEFAULT 'none' COMMENT '攻击类型 (Flip, Backdoor)',
                cpu_cores INT COMMENT 'CPU核心数',
                total_memory_gb FLOAT COMMENT '总内存(GB)',
                tflops FLOAT COMMENT 'FP16算力 (TFLOPS)',
                tee_type VARCHAR(20) COMMENT '可信环境类型 (如 TDX, SGX)',
                is_malicious BOOLEAN DEFAULT FALSE COMMENT '是否恶意节点',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB COMMENT='设备静态画像表';
            """
            cursor.execute(table_profiles)

            # 4. 创建 telemetry_logs 表 (运行时遥测)
            # 优化方案: 使用 Partition 分区表，按设备ID哈希分 10 个区
            # 注意: Partition Key 必须包含在主键中
            # 4. 创建 telemetry_logs 表 (运行时遥测)
            # 优化方案: 使用 Partition 分区表，按设备ID哈希分 10 个区
            # 注意: Partition Key 必须包含在主键中
            # [Refactor] Timestamp -> Step (Int)
            table_logs = """
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INT AUTO_INCREMENT,
                device_id VARCHAR(50) NOT NULL,
                step INT NOT NULL COMMENT '逻辑步数',
                phase VARCHAR(20) COMMENT '当前阶段 (Idle, Forward, etc)',
                cpu_usage FLOAT COMMENT 'CPU使用率(%)',
                memory_usage_mb FLOAT COMMENT '内存使用量(MB)',
                gpu_util FLOAT COMMENT 'GPU利用率(%)',
                temperature_c FLOAT COMMENT '核心温度(℃)',
                fan_speed_rpm INT COMMENT '风扇转速(RPM)',
                latency_ms FLOAT COMMENT '网络延迟(ms)',
                PRIMARY KEY (id, device_id),
                KEY idx_phase_step (device_id, phase, step)
            ) ENGINE=InnoDB COMMENT='设备运行时遥测日志表'
            PARTITION BY KEY(device_id)
            PARTITIONS 10;
            """
            cursor.execute(table_logs)
            # 5. 创建 simulation_status 表 (Dashboard 实时状态)
            # 作用: 替代 JSON 文件，提供中心化的状态查询
            table_status = """
            CREATE TABLE IF NOT EXISTS simulation_status (
                client_id INT PRIMARY KEY,
                type VARCHAR(10) DEFAULT 'GOOD',
                attack VARCHAR(20) DEFAULT 'HONEST',
                round VARCHAR(10) DEFAULT '-',
                loss VARCHAR(20) DEFAULT '-',
                asr VARCHAR(20) DEFAULT '-',
                status VARCHAR(20) DEFAULT 'Waiting',
                updated_at DOUBLE,
                INDEX idx_updated (updated_at)
            ) ENGINE=MEMORY COMMENT='仿真客户端实时状态表(内存表)';
            """
            cursor.execute(table_status)

            cnx.commit()
            cursor.close()
            cnx.close()
            _init_lines.append(f"│  ✅ 表结构初始化完成 (支持分区优化 + 内存状态表){' '*8}│")
            _init_lines.append(f"└{'─'*58}┘")
            print("\n".join(_init_lines))

        except mysql.connector.Error as err:
            print(f"❌ [DBManager] Failed to init DB: {err}")
            raise

    def update_client_status(self, client_id: int, data: Dict):
        """
        更新客户端实时状态 (Upsert)
        """
        cnx = self.get_connection()
        cursor = cnx.cursor()
        
        # 确保所有字段都有默认值
        fields = {
            "client_id": client_id,
            "type": data.get("type", "GOOD"),
            "attack": data.get("attack", "HONEST"),
            "round": str(data.get("round", "-")),
            "loss": str(data.get("loss", "-")),
            "asr": str(data.get("asr", "-")),
            "status": data.get("status", "Unknown"),
            "updated_at": time.time()
        }

        sql = """
        INSERT INTO simulation_status 
        (client_id, type, attack, round, loss, asr, status, updated_at)
        VALUES (%(client_id)s, %(type)s, %(attack)s, %(round)s, %(loss)s, %(asr)s, %(status)s, %(updated_at)s)
        ON DUPLICATE KEY UPDATE
        type=VALUES(type),
        attack=VALUES(attack),
        round=VALUES(round),
        loss=VALUES(loss),
        asr=VALUES(asr),
        status=VALUES(status),
        updated_at=VALUES(updated_at)
        """
        try:
            cursor.execute(sql, fields)
            cnx.commit()
        except Exception as e:
            print(f"⚠️ [DBManager] 状态更新失败 (client {client_id}): {e}")
        finally:
            cursor.close()
            cnx.close()

    def get_all_client_status(self) -> Dict[int, Dict]:
        """
        获取所有客户端的实时状态 (for Dashboard)
        """
        cnx = self.get_connection()
        cursor = cnx.cursor(dictionary=True)
        result = {}
        try:
            cursor.execute("SELECT * FROM simulation_status")
            rows = cursor.fetchall()
            for row in rows:
                result[row['client_id']] = row
        except Exception as e:
            print(f"⚠️ [DBManager] Error fetching status: {e}")
        finally:
            cursor.close()
            cnx.close()
        return result

    def get_connection(self):
        """获取一个新的数据库连接"""
        config = self.config.copy()
        config['database'] = self.db_name
        return mysql.connector.connect(**config)

    def register_device(self, profile: dict):
        """
        注册或更新设备画像

        Args:
            profile (dict): 设备画像字典
        """
        cnx = self.get_connection()
        cursor = cnx.cursor()

        # 确保 attack_type 存在
        if "attack_type" not in profile:
            profile["attack_type"] = "none"

        sql = """
        INSERT INTO device_profiles 
        (device_id, hardware_type, attack_type, cpu_cores, total_memory_gb, tflops, tee_type, is_malicious)
        VALUES (%(device_id)s, %(hardware_type)s, %(attack_type)s, %(cpu_cores)s, %(total_memory_gb)s, %(tflops)s, %(tee_type)s, %(is_malicious)s)
        AS new_val
        ON DUPLICATE KEY UPDATE
        hardware_type=new_val.hardware_type,
        attack_type=new_val.attack_type,
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

    def insert_telemetry_batch(self, logs: List[Dict]):
        """
        批量插入遥测数据 (高吞吐)

        Args:
            logs (List[Dict]): 遥测记录列表
        """
        if not logs:
            return

        cnx = self.get_connection()
        cursor = cnx.cursor()

        sql = """
        INSERT INTO telemetry_logs 
        (device_id, step, phase, cpu_usage, memory_usage_mb, gpu_util, temperature_c, fan_speed_rpm, latency_ms)
        VALUES (%(device_id)s, %(step)s, %(phase)s, %(cpu_usage)s, %(memory_usage_mb)s, %(gpu_util)s, %(temperature_c)s, %(fan_speed_rpm)s, %(latency_ms)s)
        """
        try:
            cursor.executemany(sql, logs)
            cnx.commit()
            # print(f"    💾 Saved {len(logs)} telemetry records to DB.") 
            # 减少刷屏，仅在调用层级打印进度
        except mysql.connector.Error as err:
            print(f"Error inserting logs: {err}")
        finally:
            cursor.close()
            cnx.close()

    def clear_all_data(self):
        """
        清空所有仿真数据 (重置环境)
        
        危危险操作: 会截断 (TRUNCATE) 所有表数据!
        """
        cnx = self.get_connection()
        cursor = cnx.cursor()
        try:
            # 由于有外键约束(实际没加，但为了健壮性)，建议先关掉 check
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE telemetry_logs;")
            cursor.execute("TRUNCATE TABLE device_profiles;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            cnx.commit()
            print("🧹 [DBManager] 所有数据已清空，环境重置成功。")
        except mysql.connector.Error as err:
            print(f"Error clearing data: {err}")
        finally:
            cursor.close()
            cnx.close()

    def fetch_telemetry_by_phase(self, device_id: str, phase: str, step: int) -> Optional[Dict]:
        """
        根据 Phase 和 Step 精确获取一条遥测数据
        """
        cnx = self.get_connection()
        cursor = cnx.cursor(dictionary=True)
        try:
            # 1. First attempt: Direct fetch
            sql = """
            SELECT * FROM telemetry_logs 
            WHERE device_id = %s AND phase = %s AND step = %s
            LIMIT 1
            """
            cursor.execute(sql, (device_id, phase, step))
            row = cursor.fetchone()
            if row:
                return row
            
            # 2. Fallback: Dynamic Cyclic Fetching
            # Query the pool size (MAX step) for this phase
            # Optimization: This could be cached in memory to avoid extra DB query
            count_sql = "SELECT MAX(step) as max_step FROM telemetry_logs WHERE device_id = %s AND phase = %s"
            cursor.execute(count_sql, (device_id, phase))
            res = cursor.fetchone()
            
            if res and res['max_step'] is not None:
                max_step = res['max_step']
                # Calculate cyclic step: step % (max_step + 1)
                # Ensure we handle the case where max_step=0 (single record)
                pool_size = max_step + 1
                loop_step = step % pool_size
                
                cursor.execute(sql, (device_id, phase, loop_step))
                return cursor.fetchone()
            else:
                return None # No data pool found for this phase
                
        except mysql.connector.Error as err:
            print(f"Error fetching data: {err}")
            return None
        finally:
            cursor.close()
            cnx.close()

    def get_device_info(self, device_id: str) -> Optional[Dict]:
        """查询单个设备的静态画像"""
        cnx = self.get_connection()
        cursor = cnx.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM device_profiles WHERE device_id = %s"
            cursor.execute(sql, (device_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            cnx.close()
