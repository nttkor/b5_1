"""시간 관련 유틸리티 모듈.

현재 로컬 KST 시각 포맷팅 및 타임스탬프 생성을 지원합니다.
"""

from datetime import datetime, timezone, timedelta

KST_TIMEZONE = timezone(timedelta(hours=9))


def get_current_kst_string(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """현재 로컬 시각(KST)을 지정된 포맷의 문자열로 반환합니다.

    Args:
        fmt (str): strftime 포맷 문자열 (기본값: '%Y-%m-%d %H:%M:%S')

    Returns:
        str: 포맷팅된 KST 시각 문자열 (예: '2026-10-09 17:08:45 KST')
    """
    now = datetime.now(KST_TIMEZONE)
    base = now.strftime(fmt)
    return f"{base} KST"


if __name__ == "__main__":
    print(get_current_kst_string())
