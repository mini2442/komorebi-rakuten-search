"""Secretsをサーバー内だけで扱う。環境変数への転記・秘密値のrepr表示はしない。"""
from dataclasses import dataclass

@dataclass(frozen=True, repr=False)
class RakutenSettings:
    application_id: str = ''
    access_key: str = ''
    referer: str = ''
    affiliate_id: str = ''

    def __repr__(self):
        return 'RakutenSettings(<redacted>)'

    @classmethod
    def from_secrets(cls, secrets):
        def get(key):
            try:
                return secrets.get(key, '')
            except (FileNotFoundError, KeyError, TypeError):
                return ''
        def text(key):
            value = get(key)
            return value.strip() if isinstance(value, str) else ''
        return cls(text('RAKUTEN_APPLICATION_ID'), text('RAKUTEN_ACCESS_KEY'),
                   text('RAKUTEN_REFERER'), text('RAKUTEN_AFFILIATE_ID'))


def provider_from_secrets(secrets):
    from .providers import RakutenProvider
    return RakutenProvider(enabled=True, settings=RakutenSettings.from_secrets(secrets))
