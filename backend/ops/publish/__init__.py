"""抖音/短视频运营交付物（发布包、引流码、合规提示），不挂载主 API。"""

from ops.publish.douyin_kit import write_douyin_kit

__all__ = ["write_douyin_kit"]
