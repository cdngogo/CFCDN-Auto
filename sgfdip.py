import requests
import os
import geoip2.database

# 配置
CF_API_KEY = os.getenv('CF_API_KEY')
CF_ZONE_YID = os.getenv('CF_ZONE_YID')
CF_DNS_NAME = os.getenv('CF_DNS_NAME')
FILE_PATH = 'sgfd_ips.txt'
SGCS_FILE_PATH = 'CloudflareST/sgcs.txt'
GEOIP_DATABASE_PATH = 'GeoLite2-Country.mmdb'

# 创建MaxMind GeoIP2数据库的Reader对象
reader = geoip2.database.Reader(GEOIP_DATABASE_PATH)

# 第一步：从URL和本地文件获取IP数据
def get_ip_data():
    url1 = 'https://raw.githubusercontent.com/ymyuuu/IPDB/main/bestproxy.txt'

    response1 = requests.get(url1)
    ip_list1 = response1.text.splitlines()

    # 从本地文件获取IP数据
    ip_list2 = []
    if os.path.exists(SGCS_FILE_PATH):
        with open(SGCS_FILE_PATH, 'r') as f:
            ip_list2 = f.read().splitlines()

    # 合并并清洗IP地址列表
    ip_list = ip_list1 + ip_list2
    cleaned_ips = clean_ip_data(ip_list)
    return cleaned_ips

# 新步骤：去除IP地址中的速度信息
def clean_ip_data(ip_list):
    cleaned_ips = []
    for ip in ip_list:
        ip = ip.split('#')[0]  # 去除速度信息，只保留IP地址
        if is_valid_ip(ip):
            cleaned_ips.append(ip)
    return cleaned_ips

# 辅助函数：检查IP地址的有效性
def is_valid_ip(ip):
    try:
        if ':' in ip:
            import ipaddress
            ipaddress.IPv6Address(ip)  # 检查IPv6地址有效性
        else:
            import socket
            socket.inet_aton(ip)  # 检查IPv4地址有效性
        return True
    except (socket.error, ipaddress.AddressValueError):
        return False

# 第二步：过滤并格式化新加坡IP地址
def filter_and_format_ips(ip_list):
    singapore_ips = []
    for ip in ip_list:
        try:
            response = reader.country(ip)
            if response.country.iso_code == 'SG':
                singapore_ips.append(f"{ip}#SG")
        except Exception as e:
            print(f"Error processing IP {ip}: {e}")
    return singapore_ips

# 新步骤：去除重复的IP地址
def remove_duplicate_ips(ip_addresses):
    seen_ips = set()
    unique_ips = []
    for ip in ip_addresses:
        ip_base = ip.split('#')[0]
        if ip_base not in seen_ips:
            seen_ips.add(ip_base)
            unique_ips.append(ip)
    return unique_ips

# 第三步：将格式化后的新加坡IP地址写入到sgfd_ips.txt文件
def write_to_file(ip_addresses):
    with open(FILE_PATH, 'w') as f:
        for ip in ip_addresses:
            f.write(ip + '\n')

# 第四步：清除指定Cloudflare域名的所有DNS记录
def clear_dns_records():
    headers = {
        'Authorization': f'Bearer {CF_API_KEY}',
        'Content-Type': 'application/json',
    }

    # 获取现有的DNS记录
    dns_records_url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_YID}/dns_records'
    dns_records = requests.get(dns_records_url, headers=headers).json()

    # 删除旧的DNS记录
    for record in dns_records['result']:
        if record['name'] == CF_DNS_NAME:
            delete_url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_YID}/dns_records/{record["id"]}'
            requests.delete(delete_url, headers=headers)

# 第五步：更新Cloudflare域名的DNS记录为sgfd_ips.txt文件中的IP地址
def update_dns_records():
    with open(FILE_PATH, 'r') as f:
        ips_to_update = [line.split('#')[0].strip() for line in f]

    headers = {
        'Authorization': f'Bearer {CF_API_KEY}',
        'Content-Type': 'application/json',
    }

    dns_records_url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_YID}/dns_records'
    for ip in ips_to_update:
        data = {
            'type': 'A',
            'name': CF_DNS_NAME,
            'content': ip,
            'ttl': 60,
            'proxied': False,
        }
        response = requests.post(dns_records_url, headers=headers, json=data)
        if response.status_code == 200:
            print(f"Successfully updated DNS record for {CF_DNS_NAME} to {ip}")
        else:
            print(f"Failed to update DNS record for {CF_DNS_NAME} to {ip}. Status code: {response.status_code}")

# 主函数：按顺序执行所有步骤
def main():
    try:
        # 第一步：获取IP数据
        ip_list = get_ip_data()

        # 第二步：过滤并格式化新加坡IP地址
        singapore_ips = filter_and_format_ips(ip_list)

        # 新步骤：去除重复的IP地址
        unique_singapore_ips = remove_duplicate_ips(singapore_ips)

        # 如果没有找到符合条件的新加坡IP，则不执行任何操作
        if not unique_singapore_ips:
            print("No Singapore IPs found. Keeping existing sgfd_ips.txt file.")
            return

        # 第三步：将格式化后的新加坡IP地址写入文件
        write_to_file(unique_singapore_ips)

        # 第四步：清除指定Cloudflare域名的所有DNS记录
        clear_dns_records()

        # 第五步：更新Cloudflare域名的DNS记录为sgfd_ips.txt文件中的IP地址
        update_dns_records()

    finally:
        # 关闭MaxMind GeoIP2数据库的Reader对象
        reader.close()

if __name__ == "__main__":
    main()