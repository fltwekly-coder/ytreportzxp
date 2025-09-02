import re
import zipfile
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType

class YouTubeReporter:
    """Simple reporter that creates a Chrome WebDriver with proxy support."""

    def __init__(self, proxy: str | None = None):
        self._proxy_str = proxy

    def _create_driver(self) -> webdriver.Chrome:
        """Create a Chrome ``WebDriver`` using a proxy with authentication.

        The ``proxy`` string must be in the format ``username:password@host:port``.
        If the format is invalid or authentication details are missing, a
        ``ValueError`` is raised.
        """
        options = Options()

        if self._proxy_str:
            proxy_cfg, pluginfile = self._build_proxy(self._proxy_str)
            capabilities = webdriver.DesiredCapabilities.CHROME.copy()
            proxy_cfg.add_to_capabilities(capabilities)
            if pluginfile:
                options.add_extension(pluginfile)
            driver = webdriver.Chrome(options=options, desired_capabilities=capabilities)
        else:
            driver = webdriver.Chrome(options=options)
        return driver

    def _build_proxy(self, proxy: str) -> tuple[Proxy, str | None]:
        match = re.match(r"^(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)$", proxy)
        if not match:
            raise ValueError("Proxy must be in the format 'username:password@host:port'")

        user = match.group("user")
        password = match.group("password")
        host = match.group("host")
        port = match.group("port")

        if not user or not password:
            raise ValueError("Proxy authentication details missing; expected 'username:password@host:port'")

        proxy_cfg = Proxy()
        proxy_cfg.proxy_type = ProxyType.MANUAL
        proxy_cfg.http_proxy = f"{host}:{port}"
        proxy_cfg.ssl_proxy = f"{host}:{port}"

        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy", "tabs", "unlimitedStorage", "storage",
                "<all_urls>", "webRequest", "webRequestBlocking"
            ],
            "background": {"scripts": ["background.js"]},
            "minimum_chrome_version":"76.0.0"
        }
        """

        background_js = f"""
        chrome.proxy.settings.set({{
            value: {{mode: "fixed_servers", rules: {{singleProxy: {{scheme: "http", host: "{host}", port: {port}}}}}},
            scope: "regular"
        }}, function() {{}});
        chrome.webRequest.onAuthRequired.addListener(
            function(details, callback) {{
                callback({{authCredentials: {{username: "{user}", password: "{password}"}}}});
            }},
            {{urls: ["<all_urls>"]}},
            ['blocking']
        );
        """

        pluginfile = tempfile.mkstemp(suffix='.zip')[1]
        with zipfile.ZipFile(pluginfile, 'w') as zp:
            zp.writestr('manifest.json', manifest_json)
            zp.writestr('background.js', background_js)

        return proxy_cfg, pluginfile
