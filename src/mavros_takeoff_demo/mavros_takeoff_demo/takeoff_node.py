#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from mavros_msgs.srv import CommandBool, SetMode
from geometry_msgs.msg import PoseStamped
import time

class TakeoffNode(Node):
    def __init__(self):
        super().__init__('takeoff_node')
        self.arm_service = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.mode_service = self.create_client(SetMode, '/mavros/set_mode')
        self.pose_pub = self.create_publisher(PoseStamped, '/mavros/setpoint_position/local', 10)

        # 等待服务可用
        while not self.arm_service.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待arming服务...')
        while not self.mode_service.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待set_mode服务...')

    def takeoff(self, height=2.5):
        # 先发布一些悬停点，为切OFFBOARD做准备（PX4要求至少发布100个点）
        self.get_logger().info('正在发送悬停点...')
        for i in range(150):
            msg = PoseStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'map'
            msg.pose.position.x = 0.0
            msg.pose.position.y = 0.0
            msg.pose.position.z = height
            self.pose_pub.publish(msg)
            time.sleep(0.05)

        # 切换模式到 OFFBOARD
        mode_req = SetMode.Request()
        mode_req.custom_mode = "OFFBOARD"
        future_mode = self.mode_service.call_async(mode_req)
        rclpy.spin_until_future_complete(self, future_mode, timeout_sec=5.0)
        if future_mode.result() is not None and future_mode.result().mode_sent:
            self.get_logger().info('OFFBOARD模式设置成功喵')
        else:
            self.get_logger().error('OFFBOARD模式设置失败，请检查MAVROS连接喵')
            return

        # 解锁
        arm_req = CommandBool.Request()
        arm_req.value = True
        future_arm = self.arm_service.call_async(arm_req)
        rclpy.spin_until_future_complete(self, future_arm, timeout_sec=5.0)
        if future_arm.result() is not None and future_arm.result().success:
            self.get_logger().info('无人机解锁成功，即将起飞喵！')
        else:
            self.get_logger().error('解锁失败，可能原因：未上电/安全开关/前一个起飞未降落喵')
            return

        self.get_logger().info('起飞指令已发送，无人机将飞至 {} 米高度悬停喵'.format(height))

        # 持续发布悬停点，保持 OFFBOARD 模式
        self.get_logger().info('持续发布悬停点，保持无人机悬停... 按 Ctrl+C 停止')
        while rclpy.ok():
            msg = PoseStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'map'
            msg.pose.position.x = 0.0
            msg.pose.position.y = 0.0
            msg.pose.position.z = height
            self.pose_pub.publish(msg)
            time.sleep(0.05)  # 20Hz

def main(args=None):
    rclpy.init(args=args)
    node = TakeoffNode()
    try:
        node.takeoff(2.5)
    except KeyboardInterrupt:
        node.get_logger().info('用户中断，节点关闭喵')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
