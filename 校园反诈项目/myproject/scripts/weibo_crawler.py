#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博反诈话题爬虫脚本
功能：从微博抓取#校园诈骗#、#反诈#、#电信诈骗#话题的内容
"""

import time
import random
import logging
import csv
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weibo_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WeiboCrawler:
    def __init__(self):
        # 初始化浏览器
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = 'https://weibo.com'
        self.results = []
    
    def login(self, username, password):
        """模拟登录微博"""
        try:
            self.driver.get(self.base_url)
            time.sleep(random.uniform(2, 4))
            
            # 点击登录按钮
            login_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@node-type="loginBtn"]')))
            login_btn.click()
            time.sleep(random.uniform(1, 3))
            
            # 切换到账号密码登录
            pwd_login = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "密码登录")]')))
            pwd_login.click()
            time.sleep(random.uniform(1, 2))
            
            # 输入账号密码
            username_input = self.wait.until(EC.presence_of_element_located((By.ID, 'loginname')))
            password_input = self.wait.until(EC.presence_of_element_located((By.NAME, 'password')))
            
            username_input.send_keys(username)
            time.sleep(random.uniform(1, 2))
            password_input.send_keys(password)
            time.sleep(random.uniform(1, 2))
            
            # 点击登录
            submit_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@node-type="submit"]')))
            submit_btn.click()
            time.sleep(random.uniform(3, 5))
            
            # 检查是否登录成功
            if '微博-随时随地发现新鲜事' in self.driver.title:
                logger.info('登录成功')
                return True
            else:
                logger.warning('登录可能失败，需要人工验证')
                # 这里可以添加人工验证的提示
                time.sleep(30)  # 给用户时间进行人工验证
                if '微博-随时随地发现新鲜事' in self.driver.title:
                    logger.info('人工验证成功')
                    return True
                else:
                    logger.error('登录失败')
                    return False
        except Exception as e:
            logger.error(f'登录失败: {str(e)}')
            return False
    
    def search_topic(self, topic, pages=5):
        """搜索话题并抓取内容"""
        try:
            # 构建搜索URL
            search_url = f'{self.base_url}/search?q={topic}&type=all'
            self.driver.get(search_url)
            time.sleep(random.uniform(2, 4))
            
            for page in range(1, pages + 1):
                logger.info(f'抓取{topic}第{page}页')
                
                # 等待页面加载完成
                time.sleep(random.uniform(3, 5))
                
                # 抓取微博内容
                self._parse_weibo_page(topic)
                
                # 翻页
                if page < pages:
                    try:
                        next_page = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//a[@class="page next S_txt1 S_line1"]')))
                        next_page.click()
                        time.sleep(random.uniform(3, 5))
                    except Exception as e:
                        logger.warning(f'翻页失败: {str(e)}')
                        break
        except Exception as e:
            logger.error(f'搜索话题失败: {str(e)}')
    
    def _parse_weibo_page(self, topic):
        """解析微博页面内容"""
        try:
            # 找到所有微博卡片
            weibo_cards = self.driver.find_elements(By.XPATH, '//div[@class="card-wrap"]')
            
            for card in weibo_cards:
                try:
                    # 用户昵称
                    nickname = card.find_element(By.XPATH, './/a[@class="name"]').text
                    
                    # 发布时间
                    try:
                        time_element = card.find_element(By.XPATH, './/span[@class="time"]')
                        post_time = time_element.text
                    except NoSuchElementException:
                        post_time = '未知'
                    
                    # 微博内容
                    try:
                        content_element = card.find_element(By.XPATH, './/div[@class="content"]/p')
                        content = content_element.text
                    except NoSuchElementException:
                        content = '无内容'
                    
                    # 转发/评论/点赞数
                    try:
                        stats = card.find_elements(By.XPATH, './/div[@class="card-act"]//a')
                        reposts = stats[0].text if len(stats) > 0 else '0'
                        comments = stats[1].text if len(stats) > 1 else '0'
                        likes = stats[2].text if len(stats) > 2 else '0'
                    except Exception:
                        reposts, comments, likes = '0', '0', '0'
                    
                    # 微博链接
                    try:
                        link_element = card.find_element(By.XPATH, './/a[@class="S_txt1"]')
                        link = link_element.get_attribute('href')
                    except NoSuchElementException:
                        link = '无链接'
                    
                    # 保存结果
                    self.results.append({
                        'topic': topic,
                        'nickname': nickname,
                        'post_time': post_time,
                        'content': content,
                        'reposts': reposts,
                        'comments': comments,
                        'likes': likes,
                        'link': link
                    })
                    
                    logger.info(f'抓取到微博: {nickname} - {content[:50]}...')
                    
                    # 随机延时，避免被封
                    time.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    logger.warning(f'解析微博失败: {str(e)}')
                    continue
        except Exception as e:
            logger.error(f'解析页面失败: {str(e)}')
    
    def save_to_csv(self, filename):
        """保存结果到CSV文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['topic', 'nickname', 'post_time', 'content', 'reposts', 'comments', 'likes', 'link']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.results)
            
            logger.info(f'保存成功，共{len(self.results)}条数据')
        except Exception as e:
            logger.error(f'保存失败: {str(e)}')
    
    def close(self):
        """关闭浏览器"""
        try:
            self.driver.quit()
            logger.info('浏览器已关闭')
        except Exception as e:
            logger.error(f'关闭浏览器失败: {str(e)}')

def main():
    """主函数"""
    crawler = WeiboCrawler()
    
    try:
        # 登录微博（需要手动输入账号密码）
        username = input('请输入微博账号: ')
        password = input('请输入微博密码: ')
        
        if not crawler.login(username, password):
            logger.error('登录失败，退出程序')
            return
        
        # 搜索话题
        topics = ['#校园诈骗#', '#反诈#', '#电信诈骗#']
        for topic in topics:
            logger.info(f'开始抓取话题: {topic}')
            crawler.search_topic(topic, pages=10)  # 每个话题抓取10页
            # 随机延时，避免被封
            time.sleep(random.uniform(5, 10))
        
        # 保存结果
        crawler.save_to_csv('data/weibo_cases.csv')
        
    except Exception as e:
        logger.error(f'程序出错: {str(e)}')
    finally:
        crawler.close()

if __name__ == '__main__':
    main()
