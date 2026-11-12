

class ABCError(Exception):
    def __init__(self, /, **kwargs):
        self.message = self._message.format(**kwargs)
        super().__init__(self.message)


class ServerError(ABCError):
    _message = "[ServerError] Unhandled server error: {e}"
    code = 500

class ClientError(ABCError):
    _message = "[ClientError] Unhandled client error: {e}"
    code = 400
    
class StartupError(ServerError):
    _message = "[StartupError] Startup error: {e}"
    code = 500

class BrowserRouterError(ServerError):
    _message = "[BrowserRouterError] Browser router error: {} "
    code = 500

class UsupportedMethodError(ClientError):
    _message = "[UnsupportedMethodError] Unsupported method: {} "
    code = 421

class UnknownContextError(ClientError):
    _message = "[UnknownContextError] Unknown context: {} "
    code = 422

class DomainNotFoundError(ClientError):
    _message = "[DomainNotFoundError] Domain not found: {domain}. Verify that it is correctly configured in the ruleset for {context}"
    code = 423

