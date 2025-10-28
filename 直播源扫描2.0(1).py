import requests
import concurrent.futures
import time
import logging
import re
import os
import socket
from typing import List, Dict
import sys
import requests.packages.urllib3.util.connection as urllib3_connection

class IDRangeScanner:
    def __init__(self, timeout=5, max_workers=20):
        self.timeout = timeout
        self.max_workers = max_workers
        self.found_channels = []
        self.output_dir = ""
        self.network_mode = "dual_stack"  # 默认双栈模式
        
        # 先初始化日志
        self.setup_logging()
        
        # 然后设置网络
        self.setup_network("dual_stack")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
        })

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_network(self, network_mode="dual_stack"):
        """
        设置网络模式
        :param network_mode: ipv4, ipv6, dual_stack
        """
        self.network_mode = network_mode
        
        if network_mode == "ipv6":
            # 强制使用IPv6
            def _allowed_gai_family():
                return socket.AF_INET6
            urllib3_connection.allowed_gai_family = _allowed_gai_family
            if hasattr(self, 'logger'):
                self.logger.info("已启用IPv6 only模式")
            else:
                print("✅ 已启用IPv6 only模式")
            
        elif network_mode == "ipv4":
            # 强制使用IPv4
            def _allowed_gai_family():
                return socket.AF_INET
            urllib3_connection.allowed_gai_family = _allowed_gai_family
            if hasattr(self, 'logger'):
                self.logger.info("已启用IPv4 only模式")
            else:
                print("✅ 已启用IPv4 only模式")
            
        else:
            # 双栈模式 (IPv6优先)
            def _allowed_gai_family():
                family = socket.AF_INET
                try:
                    # 检查系统是否支持IPv6
                    socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    # 优先尝试IPv6，失败时回退到IPv4
                    family = socket.AF_INET6
                except:
                    family = socket.AF_INET
                return family
            urllib3_connection.allowed_gai_family = _allowed_gai_family
            if hasattr(self, 'logger'):
                self.logger.info("已启用双栈模式 (IPv6优先)")
            else:
                print("✅ 已启用双栈模式 (IPv6优先)")

    def get_writable_directories(self):
        """获取可写入的目录列表"""
        writable_dirs = []
        
        # 可能的可写入目录
        possible_dirs = [
            os.getcwd(),  # 当前工作目录
            "./",         # 当前目录
            "./直播源/",   # 当前目录下的子目录
            "/data/data/com.cscjapp.python/files/",  # 应用数据目录
            "/storage/emulated/0/Download/",  # 下载目录（通常可写）
            "/sdcard/Download/",  # 下载目录别名
        ]
        
        # 检查当前环境的特殊目录
        try:
            # 如果是QPython等环境，可能有特殊目录
            app_root = os.path.dirname(os.path.abspath(__file__))
            possible_dirs.append(app_root)
            possible_dirs.append(os.path.join(app_root, "直播源"))
        except:
            pass
        
        print("\n🔍 正在检测可写入目录...")
        for dir_path in possible_dirs:
            if self.test_directory_write(dir_path):
                writable_dirs.append(dir_path)
                print(f"✅ 可写入: {dir_path}")
            else:
                print(f"❌ 不可写: {dir_path}")
        
        return writable_dirs

    def test_directory_write(self, dir_path):
        """测试目录是否可写"""
        try:
            # 确保目录存在
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except:
                    return False
            
            # 测试写入
            test_file = os.path.join(dir_path, "test_write.tmp")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("写入测试")
            
            # 测试读取和删除
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            os.remove(test_file)
            
            return content == "写入测试"
        except:
            return False

    def get_user_input(self):
        """获取用户输入的扫描参数"""
        print("\n" + "="*50)
        print("辽宁移动PLTV群:1170100 直播源扫描器1.0 - 支持IPv4/IPv6")
        print("="*50)
        
        # 网络配置选择
        print("\n🌐 网络配置:")
        print("1. IPv4 only (默认)")
        print("2. IPv6 only") 
        print("3. 双栈模式 (IPv6优先，推荐)")
        
        ip_choice = input("选择网络模式 (1-3, 默认1): ").strip()
        if ip_choice == "2":
            network_mode = "ipv6"
            print("✅ 已启用IPv6 only模式")
        elif ip_choice == "3":
            network_mode = "dual_stack"
            print("✅ 已启用双栈模式 (IPv6优先)")
        else:
            network_mode = "ipv4"
            print("✅ 使用IPv4模式")
        
        # 设置网络模式
        self.setup_network(network_mode)
        
        # 首先检测可写入目录
        writable_dirs = self.get_writable_directories()
        
        if not writable_dirs:
            print("❌ 未找到可写入的目录！")
            print("请检查应用存储权限或使用其他目录")
            return None, None, None
        
        print(f"\n请选择保存目录（输入数字）:")
        for i, dir_path in enumerate(writable_dirs, 1):
            print(f"{i}. {dir_path}")
        
        while True:
            try:
                choice = input(f"选择目录 (1-{len(writable_dirs)}): ").strip()
                if not choice:
                    continue
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(writable_dirs):
                    self.output_dir = writable_dirs[choice_num - 1]
                    print(f"✅ 已选择目录: {self.output_dir}")
                    break
                else:
                    print(f"请输入 1-{len(writable_dirs)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
        
        # 获取基础URL
        print("\n请输入要扫描的基础URL（用 {} 表示ID位置）：")
        print("示例1 (IPv4): http://example.com/PLTV/11/224/{}/index.m3u8")
        print("示例2 (IPv6): http://[2409:8087:1e01:20::28]/PLTV/11/224/322122{}/1.m3u8")
        print("注意：IPv6地址必须用方括号 [] 括起来")
        
        while True:
            base_url = input("基础URL: ").strip()
            if not base_url:
                print("URL不能为空，请重新输入")
                continue
            if "{}" not in base_url:
                print("URL中必须包含 {} 来表示ID位置")
                continue
            
            # 验证IPv6地址格式
            if self.has_ipv6_address(base_url) and "[" not in base_url:
                print("❌ IPv6地址必须用方括号 [] 括起来，例如: http://[2409:8087:1e01:20::28]/path/{}/file.m3u8")
                continue
                
            break
        
        # 获取起始ID
        while True:
            try:
                start_id = int(input("起始ID: ").strip())
                break
            except ValueError:
                print("请输入有效的数字")
        
        # 获取结束ID
        while True:
            try:
                end_id = int(input("结束ID: ").strip())
                if end_id < start_id:
                    print("结束ID不能小于起始ID")
                    continue
                break
            except ValueError:
                print("请输入有效的数字")
        
        # 获取线程数
        while True:
            try:
                workers = input(f"并发线程数 (默认{self.max_workers}): ").strip()
                if workers:
                    workers = int(workers)
                    if 1 <= workers <= 100:
                        self.max_workers = workers
                    else:
                        print("线程数应在1-100之间")
                break
            except ValueError:
                print("请输入有效的数字")
        
        # 获取超时时间
        while True:
            try:
                timeout_input = input(f"超时时间秒 (默认{self.timeout}): ").strip()
                if timeout_input:
                    self.timeout = int(timeout_input)
                break
            except ValueError:
                print("请输入有效的数字")
        
        return base_url, start_id, end_id

    def has_ipv6_address(self, url: str) -> bool:
        """检查URL是否包含IPv6地址"""
        ipv6_pattern = r'[0-9a-fA-F:]+:[0-9a-fA-F:]+'
        return bool(re.search(ipv6_pattern, url))

    def generate_url(self, base_url: str, id_num: int) -> str:
        """根据ID生成完整URL，处理IPv6地址的特殊情况"""
        try:
            # 直接格式化
            url = base_url.format(id_num)
            
            # 对于包含IPv6地址的URL，确保格式正确
            if self.has_ipv6_address(url):
                # 检查IPv6地址是否被正确括在方括号中
                if '[' not in url and ']' not in url:
                    # 提取IPv6地址并添加方括号
                    ipv6_match = re.search(r'([0-9a-fA-F:]+:[0-9a-fA-F:]+)', url)
                    if ipv6_match:
                        ipv6_addr = ipv6_match.group(1)
                        # 替换为带方括号的格式
                        url = url.replace(ipv6_addr, f'[{ipv6_addr}]')
            
            return url
        except Exception as e:
            self.logger.error(f"生成URL失败: {str(e)}")
            return base_url.format(id_num)

    def extract_channel_name(self, url: str, content: str = "") -> str:
        """尝试从URL或内容中提取频道名称"""
        # 从M3U8内容中提取
        if content and '#EXTINF' in content:
            extinf_match = re.search(r'#EXTINF:.*?,(.+?)\n', content)
            if extinf_match:
                name = extinf_match.group(1).strip()
                # 清理名称中的特殊字符
                name = re.sub(r'[<>:"/\\|?*]', '', name)
                if name and name != "-":
                    return name
        
        # 从URL中提取可能的频道信息
        url_parts = url.split('/')
        for part in url_parts:
            if 'index.m3u8' in part or part.isdigit() or '1.m3u8' in part:
                continue
            if part and len(part) > 1 and not part.startswith('322122'):
                return f"{part}"
        
        # 尝试从ID部分提取
        id_match = re.search(r'322122(\d+)/1\.m3u8', url)
        if id_match:
            return f"ID_{id_match.group(1)}"
        
        # 默认使用ID作为名称
        id_match = re.search(r'/(\d+)/[^/]*\.m3u8', url)
        if id_match:
            return f"频道_{id_match.group(1)}"
        
        return "直播频道"

    def check_single_id(self, base_url: str, id_num: int) -> Dict:
        """检查单个ID对应的直播源"""
        url = self.generate_url(base_url, id_num)
        result = {
            'id': id_num,
            'url': url,
            'valid': False,
            'channel_name': '',
            'response_time': 0,
            'content_type': '',
            'content_length': 0,
            'error': '',
            'm3u8_content': '',
            'ip_version': self.get_ip_version_from_url(url)
        }
        
        try:
            # 对于IPv6 URL，进行特殊处理
            if self.has_ipv6_address(url):
                # 验证IPv6 URL格式
                if '[' not in url or ']' not in url:
                    result['error'] = 'IPv6地址格式错误，缺少方括号'
                    return result
            
            start_time = time.time()
            
            # 对于M3U8文件，直接使用GET请求
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                # 检查是否是有效的M3U8文件
                if '#EXTM3U' in response.text:
                    result.update({
                        'valid': True,
                        'response_time': round(response_time, 2),
                        'content_type': response.headers.get('content-type', ''),
                        'content_length': len(response.text),
                        'm3u8_content': response.text
                    })
                    result['channel_name'] = self.extract_channel_name(url, response.text)
                else:
                    result['error'] = '不是有效的M3U8文件'
            else:
                result['error'] = f'HTTP {response.status_code}'
                
        except requests.exceptions.RequestException as e:
            result['error'] = str(e)
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            
        return result

    def get_ip_version_from_url(self, url: str) -> str:
        """从URL中判断使用的IP版本"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            hostname = parsed.hostname
            
            if not hostname:
                return "Unknown"
            
            # 检查是否是IPv6地址（在方括号中）
            if hostname.startswith('[') and hostname.endswith(']'):
                return "IPv6"
            # 检查是否是裸IPv6地址（不应该出现这种情况）
            elif ':' in hostname and hostname.count(':') >= 2:
                return "IPv6"
            # 检查是否是IPv4地址
            elif re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
                return "IPv4"
            else:
                # 域名，根据当前网络模式判断
                return self.network_mode.upper()
                
        except:
            return "Unknown"

    def scan_id_range(self, base_url: str, start_id: int, end_id: int, batch_size=1000) -> List[Dict]:
        """扫描ID范围"""
        self.found_channels = []
        total_ids = end_id - start_id + 1
        
        self.logger.info(f"开始扫描ID范围: {start_id} - {end_id} (共{total_ids}个ID)")
        self.logger.info(f"基础URL模式: {base_url}")
        self.logger.info(f"网络模式: {self.network_mode}")
        self.logger.info(f"线程数: {self.max_workers}, 超时: {self.timeout}秒")
        self.logger.info(f"保存目录: {self.output_dir}")
        
        # 先测试一个URL看看格式是否正确
        test_url = self.generate_url(base_url, start_id)
        self.logger.info(f"测试URL格式: {test_url}")
        
        # 分批扫描以避免内存问题
        for batch_start in range(start_id, end_id + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_id)
            batch_ids = range(batch_start, batch_end + 1)
            
            self.logger.info(f"扫描批次: {batch_start} - {batch_end}")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任务
                future_to_id = {
                    executor.submit(self.check_single_id, base_url, id_num): id_num 
                    for id_num in batch_ids
                }
                
                completed = 0
                batch_found = 0
                
                for future in concurrent.futures.as_completed(future_to_id):
                    id_num = future_to_id[future]
                    completed += 1
                    
                    try:
                        result = future.result()
                        if result['valid']:
                            self.found_channels.append(result)
                            batch_found += 1
                            ip_info = f"[{result['ip_version']}]"
                            self.logger.info(f"✅ 发现频道: {result['channel_name']} {ip_info} (ID: {id_num}, 响应: {result['response_time']}s)")
                        else:
                            # 只在调试时显示错误
                            if completed % 50 == 0:
                                self.logger.debug(f"ID {id_num} 无效: {result['error']}")
                        
                        # 显示进度
                        if completed % 100 == 0 or completed == len(batch_ids):
                            progress = (batch_start - start_id + completed) / total_ids * 100
                            self.logger.info(f"进度: {progress:.1f}% | 已扫描: {batch_start - start_id + completed}/{total_ids} | 发现: {len(self.found_channels)}")
                            
                    except Exception as e:
                        self.logger.error(f"❌ 检查ID {id_num} 失败: {str(e)}")
            
            # 批次间短暂暂停
            if batch_end < end_id:
                time.sleep(1)
        
        self.logger.info(f"扫描完成! 共找到 {len(self.found_channels)} 个有效频道")
        return self.found_channels

    def save_results(self, custom_filename: str = None):
        """保存扫描结果到指定目录，只保留有效地址"""
        if not self.found_channels:
            self.logger.warning("没有找到任何有效频道，跳过保存")
            print("⚠️ 没有找到有效频道，没有生成文件")
            return None, None
            
        # 生成文件名
        if custom_filename:
            filename = custom_filename
        else:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"有效直播源_{timestamp}.txt"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # 只保存有效的直播源，格式：频道名称,URL
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# 有效直播源列表\n")
                f.write(f"# 扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 网络模式: {self.network_mode}\n")
                f.write(f"# 总计: {len(self.found_channels)} 个有效频道\n")
                f.write(f"# 保存路径: {filepath}\n\n")
                
                # 按频道名称排序
                sorted_channels = sorted(self.found_channels, key=lambda x: x['channel_name'])
                
                # 使用序号作为频道名称
                for i, channel in enumerate(sorted_channels, 1):
                    # 格式：频道1,http://example.com/url.m3u8
                    f.write(f"频道{i},{channel['url']}\n")
            
            self.logger.info(f"有效直播源已保存到: {filepath}")
            
            # 同时生成一个带响应时间和IP版本的详细版本
            detail_filename = f"详细_{filename}"
            detail_filepath = os.path.join(self.output_dir, detail_filename)
            
            with open(detail_filepath, 'w', encoding='utf-8') as f:
                f.write("# 有效直播源详细列表\n")
                f.write(f"# 扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 网络模式: {self.network_mode}\n")
                f.write(f"# 总计: {len(self.found_channels)} 个有效频道\n\n")
                
                # 按响应时间排序
                sorted_by_speed = sorted(self.found_channels, key=lambda x: x['response_time'])
                
                for i, channel in enumerate(sorted_by_speed, 1):
                    f.write(f"# 频道{i} - {channel['channel_name']}\n")
                    f.write(f"# 响应时间: {channel['response_time']}s | IP版本: {channel['ip_version']} | ID: {channel['id']}\n")
                    f.write(f"频道{i},{channel['url']}\n\n")
            
            self.logger.info(f"详细版本已保存到: {detail_filepath}")
            
            # 显示保存信息
            print(f"\n✅ 文件保存成功！")
            print(f"📁 保存目录: {self.output_dir}")
            print(f"📄 主文件: {filename}")
            print(f"📋 详细文件: {detail_filename}")
            print(f"📊 共保存 {len(self.found_channels)} 个有效频道")
            print(f"🌐 网络模式: {self.network_mode}")
            
            # 显示文件完整路径
            print(f"\n🔍 文件完整路径:")
            print(f"   {filepath}")
            print(f"   {detail_filepath}")
            
            # 显示文件内容预览
            print(f"\n📝 文件格式预览:")
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-5:]:  # 显示最后5行
                    if line.strip() and not line.startswith('#'):
                        print(f"   {line.strip()}")
            
            return filepath, detail_filepath
            
        except Exception as e:
            self.logger.error(f"保存结果失败: {str(e)}")
            print(f"❌ 保存失败: {e}")
            return None, None

    def display_summary(self):
        """显示扫描摘要"""
        if not self.found_channels:
            print("\n没有找到任何有效频道")
            return
        
        print("\n" + "="*80)
        print("扫描结果摘要")
        print("="*80)
        
        # 按响应时间排序
        sorted_channels = sorted(self.found_channels, key=lambda x: x['response_time'])
        
        print(f"{'序号':<3} {'频道名称':<20} {'IP版本':<8} {'ID':<12} {'响应时间':<8} {'状态'}")
        print("-" * 80)
        
        for i, channel in enumerate(sorted_channels[:15], 1):  # 只显示前15个
            status = "✅有效"
            print(f"{i:<3} {channel['channel_name']:<20} {channel['ip_version']:<8} {channel['id']:<12} {channel['response_time']:<6} {status}")
        
        if len(sorted_channels) > 15:
            print(f"... 还有 {len(sorted_channels) - 15} 个频道")
        
        # 统计IP版本使用情况
        ipv4_count = sum(1 for c in self.found_channels if c['ip_version'] == 'IPv4')
        ipv6_count = sum(1 for c in self.found_channels if c['ip_version'] == 'IPv6')
        dual_count = len(self.found_channels) - ipv4_count - ipv6_count
        
        print("-" * 80)
        print(f"总计发现: {len(self.found_channels)} 个有效频道")
        print(f"IPv4频道: {ipv4_count} 个 | IPv6频道: {ipv6_count} 个 | 双栈频道: {dual_count} 个")
        print(f"网络模式: {self.network_mode}")
        print(f"保存目录: {self.output_dir}")

def main():
    """主函数"""
    scanner = IDRangeScanner()
    
    try:
        while True:
            # 获取用户输入
            result = scanner.get_user_input()
            if result is None:
                print("无法继续，退出程序")
                return
                
            base_url, start_id, end_id = result
            
            print(f"\n扫描配置确认:")
            print(f"基础URL: {base_url}")
            print(f"ID范围: {start_id} - {end_id}")
            print(f"网络模式: {scanner.network_mode}")
            print(f"线程数: {scanner.max_workers}")
            print(f"超时时间: {scanner.timeout}秒")
            print(f"预计扫描数量: {end_id - start_id + 1}")
            print(f"保存目录: {scanner.output_dir}")
            
            confirm = input("\n开始扫描？(y/n): ").strip().lower()
            if confirm != 'y':
                print("扫描已取消")
                continue
            
            print("\n开始扫描... 按 Ctrl+C 可以中断扫描")
            
            try:
                # 开始扫描
                found_channels = scanner.scan_id_range(base_url, start_id, end_id)
                
                # 显示结果
                scanner.display_summary()
                
                # 保存结果（只保存有效地址）
                main_file, detail_file = scanner.save_results()
                
            except KeyboardInterrupt:
                print("\n扫描被用户中断")
                if scanner.found_channels:
                    print(f"已找到 {len(scanner.found_channels)} 个有效频道，正在保存结果...")
                    scanner.save_results("中断扫描_有效直播源.txt")
            
            # 询问是否继续扫描
            continue_scan = input("\n是否继续扫描其他范围？(y/n): ").strip().lower()
            if continue_scan != 'y':
                print("感谢使用！")
                break
                
    except KeyboardInterrupt:
        print("\n程序退出")
    except Exception as e:
        print(f"程序出错: {e}")

if __name__ == "__main__":
    main()