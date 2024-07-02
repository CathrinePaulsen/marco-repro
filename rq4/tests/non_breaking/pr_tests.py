from core import get_github_session

from models.pr import extract_update_info_from_pr


def test_extract_update_info_from_pr_1():
    with get_github_session() as session:
        r = session.get_repo("meteorOSS/wechat-bc")
    pr = r.get_pull(11)
    ga, v_old, v_new = extract_update_info_from_pr(pr)
    assert ga == "com.alibaba:fastjson"
    assert v_old == "2.0.31"
    assert v_new == "2.0.46"


def test_extract_update_info_from_pr_2():
    with get_github_session() as session:
        r = session.get_repo("Flmelody/windward")
    pr = r.get_pull(13)
    ga, v_old, v_new = extract_update_info_from_pr(pr)
    print(f"Bumps {ga} from {v_old} to {v_new}")
    assert ga == "com.fasterxml.jackson.core:jackson-databind"
    assert v_old == "2.15.2"
    assert v_new == "2.15.3"


def test_extract_update_info_from_pr_3():
    with get_github_session() as session:
        r = session.get_repo("KouShenhai/KCloud-Platform-Alibaba")
    pr = r.get_pull(907)
    ga, v_old, v_new = extract_update_info_from_pr(pr)
    print(f"Bumps {ga} from {v_old} to {v_new}")
    assert not ga
    assert v_old == "2.2.4-OEM"
    assert v_new == "2.2.4-x86"

    eligible = True if ga and v_old and v_new else False
    assert not eligible


def test_extract_update_info_from_pr_4():
    with get_github_session() as session:
            r = session.get_repo("KouShenhai/KCloud-Platform-Alibaba")
    pr = r.get_pull(556)
    ga, v_old, v_new = extract_update_info_from_pr(pr)
    print(f"Bumps {ga} from {v_old} to {v_new}")
    assert ga == "org.springframework.kafka:spring-kafka"
    assert v_old == "3.0.4"
    assert v_new == "3.0.10"