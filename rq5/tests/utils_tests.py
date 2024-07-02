from rq5.utils import parse_dependency_command_output, get_special_version
from core import GAV


def create_gav_from_string(string: str) -> GAV:
    parts = string.split(":")
    if len(parts) == 5:
        return GAV(group_id=parts[0], artifact_id=parts[1], packaging=parts[2], version=parts[3], scope=parts[4])
    if len(parts) == 6:
        return GAV(group_id=parts[0], artifact_id=parts[1], packaging=parts[2], classifier=parts[3],
                   version=parts[4], scope=parts[5])


def test_get_special_version_release():
    g = "org.eclipse.collections"
    a = "eclipse-collections"
    actual_v = get_special_version(g, a, "release")
    expected_v = "12.0.0.M3"
    assert actual_v == expected_v


def test_get_special_version_latest():
    g = "org.eclipse.collections"
    a = "eclipse-collections"
    actual_v = get_special_version(g, a, "latest")
    expected_v = "12.0.0.M3"
    assert actual_v == expected_v

def test_parse_dependency_tree_2():
    output = """
[INFO] Scanning for projects...
[INFO]
[INFO] ---------------< io.projectdiscovery:nuclei-burp-plugin >---------------
[INFO] Building Nuclei Burp Suite plugin 1.1.3-SNAPSHOT
[INFO]   from pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[INFO]
[INFO] --- dependency:3.6.1:tree (default-cli) @ nuclei-burp-plugin ---
[INFO] io.projectdiscovery:nuclei-burp-plugin:jar:1.1.3-SNAPSHOT
[INFO] +- org.yaml:snakeyaml:jar:1.33:compile
[INFO] +- com.google.code.gson:gson:jar:2.10.1:compile
[INFO] +- com.fifesoft:rsyntaxtextarea:jar:3.3.4:compile
[INFO] +- com.fifesoft:autocomplete:jar:3.3.1:compile
[INFO] |  \- (com.fifesoft:rsyntaxtextarea:jar:3.3.2:compile - omitted for conflict with 3.3.4)
[INFO] \- org.jetbrains:annotations:jar:24.1.0:compile
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  0.689 s
[INFO] Finished at: 2024-04-21T15:14:23+02:00
[INFO] ------------------------------------------------------------------------
"""
    actual_gavs = parse_dependency_command_output(output, "dependency:tree")
    expected_gavs = [
        create_gav_from_string("org.yaml:snakeyaml:jar:1.33:compile"),
        create_gav_from_string("com.google.code.gson:gson:jar:2.10.1:compile"),
        create_gav_from_string("com.fifesoft:rsyntaxtextarea:jar:3.3.4:compile"),
        create_gav_from_string("com.fifesoft:autocomplete:jar:3.3.1:compile"),
        create_gav_from_string("com.fifesoft:rsyntaxtextarea:jar:3.3.2:compile"),
        create_gav_from_string("org.jetbrains:annotations:jar:24.1.0:compile"),
    ]
    assert actual_gavs == expected_gavs


def test_parse_dependency_tree_1():
    output = """
[INFO] Scanning for projects...
[INFO]
[INFO] ------------< me.gv7.tools.burpext:captcha-killer-modified >------------
[INFO] Building captcha-killer-modified 0.17
[INFO]   from pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[INFO]
[INFO] --- dependency:3.6.1:tree (default-cli) @ captcha-killer-modified ---
[INFO] me.gv7.tools.burpext:captcha-killer-modified:jar:0.17
[INFO] +- net.portswigger.burp.extender:burp-extender-api:jar:1.7.22:compile
[INFO] +- com.alibaba:fastjson:jar:1.2.74:compile
[INFO] +- io.netty:netty-resolver-dns-native-macos:jar:osx-x86_64:4.1.101.Final:compile
[INFO] +- org.dom4j:dom4j:jar:2.0.3:compile
[INFO] +- javax.xml.bind:jaxb-api:jar:2.3.1:compile
[INFO] |  +- (org.glassfish.jaxb:txw2:jar:2.3.0:compile - omitted for duplicate)
[INFO] |  \- javax.activation:javax.activation-api:jar:1.2.0:compile
[INFO] +- com.sun.xml.bind:jaxb-impl:jar:2.3.0:compile
[INFO] +- org.glassfish.jaxb:jaxb-runtime:jar:2.3.0:compile
[INFO] |  +- org.glassfish.jaxb:jaxb-core:jar:2.3.0:compile
[INFO] |  |  +- (javax.xml.bind:jaxb-api:jar:2.3.0:compile - omitted for conflict with 2.3.1)
[INFO] |  |  +- org.glassfish.jaxb:txw2:jar:2.3.0:compile
[INFO] |  |  \- com.sun.istack:istack-commons-runtime:jar:3.0.5:compile
[INFO] |  +- org.jvnet.staxex:stax-ex:jar:1.7.8:compile
[INFO] |  \- com.sun.xml.fastinfoset:FastInfoset:jar:1.2.13:compile
[INFO] \- javax.activation:activation:jar:1.1.1:compile
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  0.761 s
[INFO] Finished at: 2024-04-21T14:13:32+02:00
[INFO] ------------------------------------------------------------------------
"""

    actual_gavs = parse_dependency_command_output(output, "dependency:tree")
    expected_gavs = [
        create_gav_from_string("net.portswigger.burp.extender:burp-extender-api:jar:1.7.22:compile"),
        create_gav_from_string("com.alibaba:fastjson:jar:1.2.74:compile"),
        create_gav_from_string("io.netty:netty-resolver-dns-native-macos:jar:osx-x86_64:4.1.101.Final:compile"),
        create_gav_from_string("org.dom4j:dom4j:jar:2.0.3:compile"),
        create_gav_from_string("javax.xml.bind:jaxb-api:jar:2.3.1:compile"),
        create_gav_from_string("org.glassfish.jaxb:txw2:jar:2.3.0:compile"),
        create_gav_from_string("javax.activation:javax.activation-api:jar:1.2.0:compile"),
        create_gav_from_string("com.sun.xml.bind:jaxb-impl:jar:2.3.0:compile"),
        create_gav_from_string("org.glassfish.jaxb:jaxb-runtime:jar:2.3.0:compile"),
        create_gav_from_string("org.glassfish.jaxb:jaxb-core:jar:2.3.0:compile"),
        create_gav_from_string("javax.xml.bind:jaxb-api:jar:2.3.0:compile"),
        create_gav_from_string("org.glassfish.jaxb:txw2:jar:2.3.0:compile"),
        create_gav_from_string("com.sun.istack:istack-commons-runtime:jar:3.0.5:compile"),
        create_gav_from_string("org.jvnet.staxex:stax-ex:jar:1.7.8:compile"),
        create_gav_from_string("com.sun.xml.fastinfoset:FastInfoset:jar:1.2.13:compile"),
        create_gav_from_string("javax.activation:activation:jar:1.1.1:compile"),
    ]
    assert actual_gavs == expected_gavs


def test_parse_dependency_list():
    output = """
[INFO]
[INFO] ------------< me.gv7.tools.burpext:captcha-killer-modified >------------
[INFO] Building captcha-killer-modified 0.17
[INFO]   from pom.xml
[INFO] --------------------------------[ jar ]---------------------------------
[INFO]
[INFO] --- dependency:3.6.1:list (default-cli) @ captcha-killer-modified ---
[INFO]
[INFO] The following files have been resolved:
[INFO]    net.portswigger.burp.extender:burp-extender-api:jar:1.7.22:compile -- module burp.extender.api (auto)
[INFO]    com.alibaba:fastjson:jar:1.2.74:compile -- module fastjson (auto)
[INFO]    org.dom4j:dom4j:jar:2.0.3:compile -- module dom4j (auto)
[INFO]    javax.xml.bind:jaxb-api:jar:2.3.0:compile -- module java.xml.bind
[INFO]    io.netty:netty-resolver-dns-native-macos:jar:osx-x86_64:4.1.101.Final:compile -- module io.netty.resolver.dns.macos.osx.x86_64 [auto]
[INFO]
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  0.701 s
[INFO] Finished at: 2024-04-19T13:17:30+02:00
[INFO] ------------------------------------------------------------------------
"""
    actual_gavs = parse_dependency_command_output(output, "dependency:list")
    expected_gavs = [
        create_gav_from_string("net.portswigger.burp.extender:burp-extender-api:jar:1.7.22:compile"),
        create_gav_from_string("com.alibaba:fastjson:jar:1.2.74:compile"),
        create_gav_from_string("org.dom4j:dom4j:jar:2.0.3:compile"),
        create_gav_from_string("javax.xml.bind:jaxb-api:jar:2.3.0:compile"),
        create_gav_from_string("io.netty:netty-resolver-dns-native-macos:jar:osx-x86_64:4.1.101.Final:compile"),
    ]
    assert actual_gavs == expected_gavs
