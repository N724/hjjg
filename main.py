import aiohttp
import json
import logging
from typing import Optional
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("maoyan_boxoffice", "Soulter", "猫眼实时票房插件", "1.0.0")
class MaoyanBoxOffice(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "https://api.pearktrue.cn/api/maoyan/"
        self.timeout = aiohttp.ClientTimeout(total=15)  # 15秒超时

    async def fetch_data(self) -> Optional[dict]:
        """获取票房数据（包含增强的错误处理）"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url) as resp:
                    # 记录原始响应文本
                    raw_text = await resp.text()
                    logger.debug(f"API原始响应: {raw_text[:200]}...")  # 截断前200字符

                    # 先检查HTTP状态码
                    if resp.status != 200:
                        logger.error(f"API请求失败 HTTP {resp.status}")
                        return None
                    
                    # 尝试解析JSON
                    try:
                        data = await resp.json()
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {str(e)}")
                        return None
                    
                    return data

        except aiohttp.ClientError as e:
            logger.error(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知异常: {str(e)}", exc_info=True)
            return None

    def _format_boxoffice(self, amount: str) -> str:
        """格式化票房数据（增强容错）"""
        try:
            if '万' in amount:
                num = float(amount.replace('万', ''))
                if num >= 10000:
                    return f"{num/10000:.2f}亿"
                return amount
            if '亿' in amount:
                return amount
            return f"{amount}（未知格式）"
        except:
            logger.warning(f"异常票房格式: {amount}")
            return amount

    @filter.command("票房排行")
    async def boxoffice_rank(self, event: AstrMessageEvent):
        '''获取实时票房排行榜'''
        try:
            # 发送等待提示
            yield CommandResult().message("🎬 正在抓取最新票房数据...")

            # 获取数据
            data = await self.fetch_data()
            if not data:
                yield CommandResult().error("📡 连接票房数据中心失败，请稍后重试~")
                return

            # 检查基础结构
            if "code" not in data or "data" not in data:
                logger.error(f"API响应结构异常: {data.keys()}")
                yield CommandResult().error("🎥 数据格式异常，请联系管理员")
                return

            # 检查状态码
            if data["code"] != 200:
                logger.error(f"API返回错误状态码: {data.get('msg')}")
                yield CommandResult().error(f"📉 数据获取失败：{data.get('msg', '未知错误')}")
                return

            # 检查data字段类型
            if not isinstance(data["data"], list):
                logger.error(f"data字段类型异常: {type(data['data'])}")
                yield CommandResult().error("🎞️ 数据解析失败，请稍后再试")
                return

            # 获取前五部电影
            movies = data["data"][:10]
            if not movies:
                yield CommandResult().message("🎥 今日影院静悄悄，暂无票房数据哦~")
                return

            # 构建消息内容
            msg = ["🐱【猫眼实时票房TOP5】🐱\n"]
            for movie in movies:
                try:
                    # 防御性字段检查
                    required_fields = ['top', 'movieName', 'sumBoxDesc', 'boxRate', 'showCountRate', 'avgSeatView']
                    if not all(field in movie for field in required_fields):
                        logger.warning(f"电影数据字段缺失: {movie.keys()}")
                        continue

                    formatted_box = self._format_boxoffice(movie["sumBoxDesc"])
                    msg.append(
                        f"🏆 第{movie['top']}名：{movie['movieName']}\n"
                        f"💰 累计票房：{formatted_box}（{movie['boxRate']}）\n"
                        f"🎫 排片占比：{movie['showCountRate']}\n"
                        f"👥 上座率：{movie['avgSeatView']}\n"
                        "🍿" + "━"*20
                    )
                except Exception as e:
                    logger.error(f"处理电影数据异常: {str(e)}", exc_info=True)
                    continue

            # 添加更新时间（防御性处理）
            timestamp = data.get("time", "").split('.')[0] if "time" in data else "未知时间"
            msg.append(f"\n⏰ 更新时间：{timestamp}")

            # 发送结果
            yield CommandResult().message("\n".join(msg)).use_t2i(False)

        except Exception as e:
            logger.error(f"处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("🎥 系统开小差了，请稍后再试~")
