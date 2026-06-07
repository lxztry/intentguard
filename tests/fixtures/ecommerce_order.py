"""
电商订单服务 - 示例代码

用于测试 IntentGuard 验证功能
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderService:
    """订单服务"""
    
    def __init__(self, db, sms_service, inventory_service):
        self.db = db
        self.sms_service = sms_service
        self.inventory = inventory_service
    
    def create_order(self, user_id: int, product_id: int, quantity: int = 1) -> dict:
        """
        创建订单
        
        Args:
            user_id: 用户ID
            product_id: 商品ID
            quantity: 数量
            
        Returns:
            订单信息
        """
        # 检查用户ID有效性
        if user_id <= 0:
            raise ValueError("无效的用户ID")
        
        # 检查库存
        if not self.inventory.check(product_id, quantity):
            raise ValueError("库存不足")
        
        # 获取商品信息
        product = self.db.fetch_one(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )
        
        if not product:
            raise ValueError("商品不存在")
        
        # 计算价格（这里可能有促销逻辑）
        price = product["price"]
        discounted_price = price * quantity
        
        # 验证促销价格不能大于原价（这个需求可能被违反）
        # TODO: 需要添加价格验证
        
        # 创建订单
        order = {
            "user_id": user_id,
            "product_id": product_id,
            "quantity": quantity,
            "original_price": price,
            "discounted_price": discounted_price,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # 保存订单
        order_id = self.db.insert("orders", order)
        order["id"] = order_id
        
        # 发送短信通知（满足需求：下单后发送短信）
        user = self.db.fetch_one("SELECT phone FROM users WHERE id = ?", (user_id,))
        if user and user.get("phone"):
            self.sms_service.send(
                user["phone"],
                f"您的订单已创建，订单号：{order_id}"
            )
        
        # 记录日志
        logger.info(f"订单创建成功: {order_id}, 用户: {user_id}")
        
        return order
    
    def cancel_order(self, order_id: int, reason: str = "") -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            reason: 取消原因
            
        Returns:
            是否成功
        """
        # 查询订单
        order = self.db.fetch_one(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        )
        
        if not order:
            logger.error(f"订单不存在: {order_id}")
            return False
        
        # 检查订单状态
        if order["status"] in ("completed", "cancelled"):
            logger.warning(f"订单状态不允许取消: {order['status']}")
            return False
        
        # 更新订单状态
        self.db.update(
            "orders",
            {"status": "cancelled", "cancel_reason": reason},
            f"id = {order_id}"
        )
        
        # 记录日志
        logger.info(f"订单已取消: {order_id}, 原因: {reason}")
        
        return True
    
    def process_payment(self, order_id: int, payment_method: str) -> dict:
        """
        处理支付
        
        Args:
            order_id: 订单ID
            payment_method: 支付方式
            
        Returns:
            支付结果
        """
        # 获取订单
        order = self.db.fetch_one(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        )
        
        if not order:
            raise ValueError("订单不存在")
        
        # 尝试处理支付
        try:
            result = self._call_payment_gateway(order, payment_method)
            
            if result["success"]:
                # 更新订单状态
                self.db.update(
                    "orders",
                    {"status": "paid", "paid_at": datetime.now().isoformat()},
                    f"id = {order_id}"
                )
                logger.info(f"支付成功: {order_id}")
            else:
                logger.error(f"支付失败: {result.get('error', '未知错误')}")
            
            return result
            
        except Exception as e:
            logger.error(f"支付异常: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _call_payment_gateway(self, order: dict, method: str) -> dict:
        """调用支付网关（模拟）"""
        # 这里应该有真实的支付逻辑
        return {
            "success": True,
            "transaction_id": f"TXN-{order['id']}"
        }


class InventoryService:
    """库存服务"""
    
    def __init__(self, db):
        self.db = db
    
    def check(self, product_id: int, quantity: int = 1) -> bool:
        """检查库存是否充足"""
        result = self.db.fetch_one(
            "SELECT stock FROM products WHERE id = ? AND stock >= ?",
            (product_id, quantity)
        )
        return result is not None
    
    def reserve(self, product_id: int, quantity: int) -> bool:
        """预留库存"""
        affected = self.db.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
            (quantity, product_id, quantity)
        )
        return affected > 0


class SMSService:
    """短信服务"""
    
    def send(self, phone: str, message: str) -> bool:
        """
        发送短信
        
        Args:
            phone: 手机号
            message: 短信内容
            
        Returns:
            是否发送成功
        """
        # 模拟发送短信
        logger.info(f"发送短信到 {phone}: {message}")
        return True