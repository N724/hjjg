import aiohttp
import logging
from typing import Optional
from astrbot.api.all import AstrMessageEvent, CommandResult, Context
from astrbot.api.star import register, Star

logger = logging.getLogger("astrbot")

@register("gold_price", "作者名", "实时黄金价格查询", "1.0.0")
class GoldPricePlugin(Star):
    def __init__(self, context: Context) -> None:
        super().__init__(context)
        self.api_url = "https://api.pearktrue.cn/api/goldprice/"
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def fetch_gold_data(self) -> Optional[dict]:
        """获取黄金数据（增强错误处理）"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.api_url) as resp:
                    raw_text = await resp.text()
                    logger.debug(f"API原始响应: {raw_text[:200]}...")

                    if resp.status != 200:
                        logger.error(f"HTTP错误: {resp.status}")
                        return None
                    
                    try:
                        return await resp.json()
                    except Exception as e:
                        logger.error(f"JSON解析失败: {str(e)}")
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"网络请求异常: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"未知异常: {str(e)}", exc_info=True)
            return None

    def _format_change(self, change: str) -> str:
        """格式化涨跌幅"""
        try:
            change_val = float(change)
            if change_val > 0:
                return f"📈 +{change}%"
            elif change_val < 0:
                return f"📉 {change}%"
            return f"➖ {change}%"
        except:
            return change

    @filter.command("gold")
    async def gold_price(self, event: AstrMessageEvent):
        '''获取实时黄金价格'''
        try:
            # 发送等待提示
            yield CommandResult().message("🔄 正在获取最新金价...")

            # 获取数据
            data = await self.fetch_gold_data()
            if not data:
                yield CommandResult().error("⚠️ 连接黄金数据中心失败，请稍后重试")
                return

            # 检查基础结构
            if data.get("code") != 200:
                logger.error(f"API错误: {data.get('msg')}")
                yield CommandResult().error(f"❌ 数据获取失败：{data.get('msg', '未知错误')}")
                return

            # 构建消息内容
            msg = [
                "💰【实时黄金价格】💰",
                f"⏰ 更新时间：{data.get('time', '未知时间')}",
                "━"*20
            ]

            for item in data.get("data", [])[:5]:  # 展示前5个品种
                try:
                    msg.append(
                        f"🔸 {item['title']}\n"
                        f"  现价：{item['price']}元/克\n"
                        f"  涨跌：{self._format_change(item['changepercent'])}\n"
                        f"  最高：{item['maxprice']} | 最低：{item['minprice']}\n"
                        "━"*20
                    )
                except KeyError as e:
                    logger.warning(f"数据字段缺失: {str(e)}")
                    continue

            msg.append(f"\n数据来源：{data.get('api_source', '')}")

            yield CommandResult().message("\n".join(msg)).use_t2i(False)

        except Exception as e:
            logger.error(f"处理指令异常: {str(e)}", exc_info=True)
            yield CommandResult().error("⚠️ 金价查询服务暂时不可用")

    @filter.command("gold_help")
    async def gold_help(self, event: AstrMessageEvent):
        """获取帮助信息"""
        help_msg = [
            "📖 使用说明：",
            "/gold - 获取主要黄金品种实时价格",
            "/gold_help - 显示本帮助信息",
            "━"*20,
            "支持品种：",
            "• 黄金延期 • 迷你黄金延期",
            "• AU9999 • 沪金95",
            "• 沪铂95 • 沪金100G"
        ]
        yield CommandResult().message("\n".join(help_msg))
