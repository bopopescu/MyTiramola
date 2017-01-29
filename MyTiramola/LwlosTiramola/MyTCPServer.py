import socketserver, json, time
import MyDecisionMaker

class MyTCPServer(socketserver.ThreadingTCPServer):
    def __init__(self, server_address, RequestHandlerClass, decisionMaker):
        socketserver.ThreadingTCPServer.__init__(self, 
                                                 server_address, 
                                                 RequestHandlerClass)
        self.decisionMaker = decisionMaker
    allow_reuse_address = True


        
class MyTCPServerHandler(socketserver.BaseRequestHandler):


    def handle(self):
        try:
            data = json.loads(self.request.recv(1024).decode('UTF-8').strip())
            # process the data, i.e. print it:
            maps = data['mappers']
            reduces = data['reducers']

            
            print('I got maps: '+maps)
            print('I got reduces: '+reduces)


            self.server.decisionMaker.takeDecision(str(maps))





            # send some 'ok' back
            self.request.sendall(bytes(json.dumps({'return':'ok'}), 'UTF-8'))
        except Exception as e:
            print("Exception wile receiving message: ", e)

