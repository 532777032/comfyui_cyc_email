import smtplib
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
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # ===== 广告开关（无实际作用，仅用于展示） =====
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
                    "default": 465,
                    "min": 1,
                    "max": 65535,
                    "tooltip": "QQ邮箱SSL端口为465，TLS端口为587"
                }),
                "使用SSL": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "使用SSL加密（端口465勾选，端口587取消）"
                }),
                "发件邮箱": ("STRING", {
                    "default": "@qq.com",
                    "multiline": False,
                    "tooltip": "请输入您的QQ邮箱地址"
                }),
                "授权码": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "",
                    "tooltip": "请输入16位QQ邮箱授权码,请登录QQ邮箱获取授权码，不是登录密码"
                }),
                "收件邮箱": ("STRING", {
                    "default": "@qq.com",
                    "multiline": False,
                    "placeholder": "",
                    "tooltip": "收件人邮箱地址,例如 receiver@example.com"
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

    def send_email(self, SMTP服务器, 端口, 使用SSL, 发件邮箱, 授权码,
                   收件邮箱, 主题, 正文, 图像=None, 任意=None, **kwargs):
        # 忽略所有额外参数（包括广告开关）
        # 处理附件（如果有图片输入）
        attachments = []
        if 图像 is not None:
            img_tensor = 图像[0].cpu().float()
            img_np = (img_tensor.numpy() * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_np, 'RGB')
            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            img_data = buffered.getvalue()
            attachments.append(('image.png', img_data, 'image/png'))

        try:
            self._send_mail(SMTP服务器, 端口, 使用SSL,
                            发件邮箱, 授权码,
                            收件邮箱, 主题, 正文, attachments)
            print("✅ 邮件发送成功")
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")

        return ()

    def _send_mail(self, SMTP服务器, 端口, 使用SSL,
                   发件邮箱, 授权码,
                   收件邮箱, 主题, 正文, attachments):
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
            part.add_header('Content-Disposition', 'attachment', filename=Header(filename, 'utf-8').encode())
            msg.attach(part)

        if 使用SSL:
            server = smtplib.SMTP_SSL(SMTP服务器, 端口, timeout=30)
        else:
            server = smtplib.SMTP(SMTP服务器, 端口, timeout=30)
            server.starttls()

        try:
            server.login(发件邮箱, 授权码)
            server.send_message(msg)
        finally:
            server.quit()

NODE_CLASS_MAPPINGS = {
    "SendEmailNode": SendEmailNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SendEmailNode": "cyc email/邮件发送 (SMTP) 🧧公众号:程序员野区",
}
