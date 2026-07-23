# How do I install the SDK?

Our official SDK is available for Python, JavaScript, and Go. Python: pip install acme-sdk. JavaScript: npm install @acme/sdk. Go: go get github.com/acme/sdk. After installation, initialize the SDK with your API key: ```python
from acme import Client
client = Client(api_key='your-key')
```. The SDK automatically handles retries, rate limiting, and pagination. See the full documentation at docs.acme.com/sdk for advanced configuration options.
