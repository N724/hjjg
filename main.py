import aiohttp
import json
import logging
from typing import Optional
from astrbot.api.all import AstrMessageEvent, CommandResult, Context, Plain
import astrbot.api.event.filter as filter
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("gold_price", "作者名", "实时黄金价格插件", "1.0.0")
class GoldPrice(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "https://api.pearktrue.cn/api/goldprice/"
        self.timeout = aiohttp.ClientTimeout(total=15)  # 15秒超时

    async def fetch_data(self) -> Optional[dict]:
        """获取黄金数据（增强错误处理）"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url) as resp:
                    raw_text = await resp.text()
                    logger.debug(f"API原始响应: {raw_text[:200]}...")

                    if resp.status != 200:
                        logger.error(f"API请求失败 HTTP {resp.status}")
                        return None
                    
                    try:
                        return await resp.json()
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {str(e)}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知异常: {str(e)}", exc_info=True)
            return None

    def _format_change(self, change: str) -> str:
        """格式化涨跌幅（增强容错）"""
        try:
            change_val = float(change)
            if change_val > 0:
                return f"📈 +{change}%"
            elif change_val < 0:
                return f"📉 {change}%"
            return f"➖ {change}%"
        except:
            logger.warning(f"异常涨跌幅格式: {change}")
            return change

    @filter.command("gold")
    async def gold_price(self, event: AstrMessageEvent):
        '''获取实时黄金价格'''
        try:
            # 发送等待提示
            yield CommandResult().message("⏳ 正在获取黄金行情...")

            # 获取数据
            data = await self.fetch_data()
            if not data:
                yield CommandResult().error("⚠️ 连接黄金数据源失败，请稍后重试")
                return

            # 检查基础结构
            if "code" not in data or "data" not in data:
                logger.error(f"API响应结构异常: {data.keys()}")
                yield CommandResult().error("❗ 数据格式异常，请联系管理员")
                return

            # 检查状态码
            if data["code"] != 200:
                logger.error(f"API返回错误状态码: {data.get('msg')}")
                yield CommandResult().error(f"❌ 数据获取失败：{data.get('msg', '未知错误')}")
                return

            # 检查data字段类型
            if not isinstance(data["data"], list):
                logger.error(f"data字段类型异常: {type(data['data'])}")
                yield CommandResult().error("❗ 数据解析失败，请稍后再试")
                return

            # 获取前五条数据
            gold_list = data["data"][:5]
            if not gold_list:
                yield CommandResult().message("🕒 当前无黄金行情数据")
                return

            # 构建消息内容
            msg = ["💰【实时黄金价格TOP5】💰\n"]
            for item in gold_list:
                try:
                    msg.append(
                        f"🔸 {item['title']}\n"
                        f"  现价：{item['price']}元/克\n"
                        f"  涨跌：{self._format_change(item['changepercent'])}\n"
                        f"  最高：{item['maxprice']} | 最低：{item['minprice']}\n"
                        "🍞" + "━"*20
                    )
                except KeyError as e:
                    logger.warning(f"数据字段缺失: {str(e)}")
                    continue

            # 添加更新时间
            timestamp = data.get("time", "").split('.')[0] if "time" in data else "未知时间"
            msg.append(f"\n⏰ 更新时间：{timestamp}")

            # 发送结果
            yield CommandResult().message("\n".join(msg)).use_t2i(False)

        except Exception as e:
            logger.error(f"处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("💥 系统开小差了，请稍后再试~")

    @filter.command("gold_help")
    async def gold_help(self, event: AstrMessageEvent):
        """获取帮助信息"""
        help_msg = [
            "📘 使用说明：",
            "/gold       - 获取实时黄金价格",
            "/gold_help  - 显示本帮助信息",
            "━"*20,
            "数据包含：",
            "• 黄金延期 • 迷你黄金延期",
            "• AU9999   • 沪金95",
            "• 沪铂95   • 更多..."
        ]
        yield CommandResult().message("\n".join(help_msg))
