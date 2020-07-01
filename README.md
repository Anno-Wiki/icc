# ICC

The ICC (Intertextual Canon Cloud) is a web app designed for a collaborative
annotations wiki of public domain literature. The only current instance of this
app can be found at [anno.wiki](https://anno.wiki)

Raw texts in various states of processing and the text processors themselves can be found at https://github.com/malan88/texts

## Environment Variables

- ICC_DEBUG         = 1 or 0
- ICC_TEST          = 1 or 0
- ICCVENV           = venv/bin/activate absolute path
- ICCDB             = IP address for mysql db
- PW                = password for mysql db
- DATABASE_URL      = python uri for mysql "mysql+pymysql://<username>:<password>@<ip>/<db>?charset=utf8mb4"
