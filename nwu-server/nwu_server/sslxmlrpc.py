from M2Crypto import SSL
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

class SSLXMLRPCServer(SSL.SSLServer, SimpleXMLRPCServer):
    def __init__(self, ssl_context, server_uri):
        handler = SimpleXMLRPCRequestHandler
        #    self.handle_error = self._quietErrorHandler
        SSL.SSLServer.__init__(self, server_uri, handler, ssl_context) 
        self.funcs = {}
        self.logRequests = 0
        self.instance = None

class SSLServer:
    
    def __init__(self,pemfile):
        self.pemfile = pemfile
        self.ssl_context = self.ctx()

    def ctx(self):
        ctx = SSL.Context()
        ctx.load_cert(self.pemfile)
#        ctx.load_client_ca(pemfile)
#        ctx.load_verify_info(pemfile)
#        ctx.set_verify(self.verify, self.verify_depth)
#        ctx.set_session_id_ctx('xmlrpcssl')
#        ctx.set_info_callback(self.callback)
        return ctx

    def start_server(self, host, port):
        ssl_context = self.ctx() 
        address = (host, port)
        server = SSLXMLRPCServer(ssl_context, address)
        return server      
