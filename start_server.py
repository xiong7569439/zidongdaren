"""
YouTube 网红曝光合作系统 - 带自动重启的启动脚本
功能:
- 服务崩溃后自动重启
- 完整的日志记录
- 优雅的错误处理
"""
import os
import sys
import time
import logging
from datetime import datetime

# 配置日志
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"web_server_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

MAX_RESTARTS = 5  # 最大重启次数
RESTART_DELAY = 3  # 重启延迟 (秒)

def start_server():
    """启动 Web 服务器"""
    logger.info("="*80)
    logger.info("开始启动 YouTube 网红曝光合作系统")
    logger.info("="*80)
    
    restart_count = 0
    
    while True:
        try:
            logger.info(f"第 {restart_count + 1} 次尝试启动服务...")
            
            # 导入并运行 Flask 应用
            from web_app import app
            
            # 生产环境配置
            debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
            
            logger.info(f"服务启动在 http://localhost:5000")
            logger.info(f"Debug 模式：{debug_mode}")
            logger.info(f"日志文件：{log_file}")
            
            # 运行应用 (使用 Flask 的 serve_forever)
            app.run(host="0.0.0.0", port=5000, debug=debug_mode, use_reloader=False)
            
            # 如果正常运行到这里，说明服务正常退出
            logger.warning("服务正常退出，准备重启...")
            
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在退出...")
            break
        except Exception as e:
            logger.error(f"服务异常退出：{str(e)}", exc_info=True)
            restart_count += 1
            
            if restart_count >= MAX_RESTARTS:
                logger.error(f"达到最大重启次数 ({MAX_RESTARTS}),停止服务")
                logger.error("请检查日志文件排查问题:" + log_file)
                break
            
            logger.info(f"{RESTART_DELAY}秒后自动重启...")
            time.sleep(RESTART_DELAY)
    
    logger.info("服务已停止")

if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        logger.critical(f"启动失败：{str(e)}", exc_info=True)
        input("按回车键退出...")
