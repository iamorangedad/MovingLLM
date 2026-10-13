class VisionParseError(Exception):
    """模型响应无法解析成家具清单。"""


class ConfigurationError(Exception):
    """缺少运行所需的配置。"""
