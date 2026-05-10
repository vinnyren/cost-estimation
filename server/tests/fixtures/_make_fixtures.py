"""一次性运行：生成测试 fixture（不进 git 历史外）"""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)

# 注册中文字体（CID 内置，无需外部字体文件）
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def make_pdf():
    c = canvas.Canvas(str(OUT / "sample.pdf"), pagesize=A4)
    c.setFont("STSong-Light", 12)
    c.drawString(50, 800, "XX 政务服务平台业务需求")
    c.drawString(50, 770, "3.2.1 门户首页")
    c.drawString(50, 750, "新闻列表 + 政务服务图标")
    c.drawString(50, 720, "3.2.2 新闻管理")
    c.drawString(50, 700, "新增、修改、删除、查看、撤回")
    c.drawString(50, 670, "3.2.3 用户管理")
    c.save()


if __name__ == "__main__":
    make_pdf()
    print("✓ sample.pdf created")
