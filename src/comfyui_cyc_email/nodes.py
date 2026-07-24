import smtplib
import ssl
import random
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
import torch
import numpy as np
from PIL import Image
import io

class SendEmailNode:
    """
    发送邮件节点（无输出），适用于工作流末尾。
    接收图片作为附件，但不返回任何数据。
    每次执行会发送邮件（由IS_CHANGED随机值强制触发）。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "公众号：程序员野区": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "如有遇到使用上的问题，可以前往公众号留言。"
                }),
                # ===== 以下为正常配置 =====
                "SMTP服务器": ("STRING", {
                    "default": "smtp.qq.com",
                    "multiline": False,
                    "placeholder": "例如 smtp.qq.com",
                    "tooltip": "QQ邮箱的SMTP服务器地址"
                }),
                "端口": ("INT", {
                    "default": 587,
                    "min": 1,
                    "max": 65535,
                    "tooltip": "推荐587（TLS）或465（SSL）"
                }),
                "使用SSL": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "端口465时勾选（SSL），端口587时取消勾选（TLS）"
                }),
                "发件邮箱": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "请填写完整QQ邮箱，例如 123456@qq.com",
                    "tooltip": "完整的QQ邮箱地址"
                }),
                "授权码": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "请输入16位QQ邮箱授权码",
                    "tooltip": "QQ邮箱授权码（16位字母数字）"
                }),
                "收件邮箱": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "收件人邮箱",
                    "tooltip": "目标邮箱地址"
                }),
                "主题": ("STRING", {
                    "default": "ComfyUI 生成完成",
                    "multiline": False,
                    "tooltip": "邮件主题"
                }),
                "正文": ("STRING", {
                    "default": "您的图片已生成，详见附件。",
                    "multiline": True,
                    "tooltip": "邮件正文，支持多行文本"
                }),
            },
            "optional": {
                "图像": ("IMAGE", {
                    "tooltip": "要作为附件发送的图片（可选）"
                }),
                "任意": ("*", {
                    "tooltip": "任意输入（仅用于触发，实际不处理）"
                }),
            }
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "send_email"
    CATEGORY = "cycNode"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """每次执行都返回不同值，强制节点重新执行"""
        return random.random()

    def send_email(self, SMTP服务器, 端口, 使用SSL, 发件邮箱, 授权码,
                   收件邮箱, 主题, 正文, 图像=None, 任意=None, **kwargs):
        """主执行函数：处理图片附件并发送邮件（带重试机制）"""
        attachments = []
        if 图像 is not None:
            img_tensor = 图像[0].cpu().float()
            img_np = (img_tensor.numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np, 'RGB')
            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            img_data = buffered.getvalue()
            attachments.append(('image.png', img_data, 'image/png'))

        # 尝试发送，最多重试2次
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                self._send_mail(SMTP服务器, 端口, 使用SSL,
                                发件邮箱, 授权码,
                                收件邮箱, 主题, 正文, attachments)
                print("✅ 邮件发送成功")
                return ()
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ 第{attempt+1}次发送失败: {error_msg}")
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数退避：1s, 2s
                    print(f"🔄 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ 邮件发送最终失败: {error_msg}")
                    # 输出更详细的诊断信息
                    print("📌 请检查：")
                    print("  1.如果使用代理或VPN，请尝试关闭")
                    print("  2. 授权码是否正确（16位，不是QQ密码）")
                    print("  3. 尝试切换端口（465/587）和SSL/TLS模式")
                    print("  4. 网络是否允许访问 smtp.qq.com 的端口（465/587）")
        return ()

    def _send_mail(self, SMTP服务器, 端口, 使用SSL,
                   发件邮箱, 授权码,
                   收件邮箱, 主题, 正文, attachments):
        """实际发送邮件的内部方法（增强SSL/TLS兼容性）"""
        msg = MIMEMultipart()
        msg['From'] = 发件邮箱
        msg['To'] = 收件邮箱
        msg['Subject'] = Header(主题, 'utf-8')
        msg.attach(MIMEText(正文, 'plain', 'utf-8'))

        for filename, data, mime_type in attachments:
            if mime_type.startswith('image/'):
                part = MIMEImage(data, name=filename)
            else:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(data)
                encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment',
                            filename=Header(filename, 'utf-8').encode())
            msg.attach(part)

        # 创建SSL上下文，指定TLS版本（兼容QQ邮箱要求）
        context = ssl.create_default_context()
        # 限制使用较新的TLS版本（QQ邮箱支持TLS 1.2/1.3）
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        # 如果需要更宽松的验证（测试用），可取消注释：
        # context.check_hostname = False
        # context.verify_mode = ssl.CERT_NONE

        if 使用SSL:
            # 端口465 SSL直连
            server = smtplib.SMTP_SSL(SMTP服务器, 端口, timeout=30, context=context)
        else:
            # 端口587 STARTTLS
            server = smtplib.SMTP(SMTP服务器, 端口, timeout=30)
            # 某些网络环境可能需要显式设置本地主机名
            # server.local_hostname = "localhost"
            server.starttls(context=context)

        try:
            server.login(发件邮箱, 授权码)
            server.send_message(msg)
        finally:
            server.quit()

# 节点注册
NODE_CLASS_MAPPINGS = {
    "SendEmailNode": SendEmailNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SendEmailNode": "cyc email/邮件发送 (SMTP) ",
}
