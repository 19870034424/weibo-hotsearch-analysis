import os
import random
import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

import requests

logger = logging.getLogger(__name__)


@dataclass
class HotSearchItem:
    rank: int
    title: str
    hot_value: int
    label: str
    category: str
    link: str
    img_url: Optional[str]
    crawl_time: str


class WeiboHotSearchCrawler:
    def __init__(self, config: Dict):
        self.config = config
        self.url = config['spider']['hotsearch_url']
        self.user_agents = config['spider']['user_agents']
        self.request_delay = config['spider']['request_delay']
        self.timeout = config['spider']['timeout']
        self.max_retries = config['spider']['max_retries']
        self.retry_delay = config['spider']['retry_delay']

        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://weibo.com/',
            'User-Agent': random.choice(self.user_agents),
        })

        # Cookie 只从配置文件或环境变量读取，严禁写死在源码中
        cookie = os.environ.get('WEIBO_COOKIE') or config['spider'].get('cookie', '')
        if cookie:
            self.session.headers['Cookie'] = cookie
        else:
            logger.warning("未配置微博Cookie（spider.cookie 或环境变量 WEIBO_COOKIE），接口可能返回418")

        self.last_crawl_time = None
        self.last_user_agent = None

    def _rotate_user_agent(self):
        self.last_user_agent = random.choice(self.user_agents)
        self.session.headers['User-Agent'] = self.last_user_agent

    def _make_request(self) -> Optional[Dict]:
        for attempt in range(self.max_retries):
            try:
                self._rotate_user_agent()
                logger.info(f"正在请求微博热搜API (第{attempt + 1}次尝试)...")

                response = self.session.get(
                    self.url,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 418:
                    logger.warning(f"被反爬 (418)，等待{self.retry_delay * 2}秒后重试...")
                    time.sleep(self.retry_delay * 2)
                else:
                    logger.warning(f"请求失败，状态码: {response.status_code}")

            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (第{attempt + 1}次尝试)")
            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)

        return None

    def _parse_response(self, data: Dict) -> List[HotSearchItem]:
        items = []

        if data.get('ok') != 1:
            logger.error(f"API返回错误: {data}")
            return items

        hot_list = data.get('data', {}).get('realtime', [])

        for item in hot_list:
            label = item.get('label_name', '')
            category = item.get('note', '')

            hot_value = item.get('num', 0)

            link = item.get('word_scheme', '')

            hot_item = HotSearchItem(
                rank=item.get('rank', 0),
                title=item.get('word', ''),
                hot_value=hot_value,
                label=label,
                category=category,
                link=link,
                img_url=item.get('img_url'),
                crawl_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            items.append(hot_item)

        return items

    def crawl(self) -> tuple[int, List[HotSearchItem]]:
        start_time = time.time()
        self.last_crawl_time = datetime.now()

        logger.info("=" * 50)
        logger.info(f"开始爬取微博热搜榜 | 爬取时间: {self.last_crawl_time}")

        data = self._make_request()

        if data is None:
            logger.error("爬取失败，无法获取数据")
            return 0, []

        items = self._parse_response(data)

        if items:
            logger.info(f"成功爬取 {len(items)} 条热搜记录")
            for item in items[:5]:
                logger.info(f"  #{item.rank} {item.title} (热度: {item.hot_value:,} | 标签: {item.label})")
        else:
            logger.warning("未解析到任何热搜数据")

        duration = time.time() - start_time
        logger.info(f"本次爬取耗时: {duration:.2f}秒")

        return len(items), items

    def crawl_and_save(self, storage) -> tuple[int, float]:
        count, items = self.crawl()

        if items:
            storage.save(items)

        return count, time.time() - self.last_crawl_time.timestamp() if self.last_crawl_time else 0
