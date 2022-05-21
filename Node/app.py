from flask import Flask, render_template, request
import sqlite3
import logging
import socket
import os
import json
import random
import traceback
import threading
import time

app = Flask(__name__)

handler = logging.FileHandler("test.log")  # Creating logger
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

containerName = os.environ["contName"]

############ Phase 1 UI Integration ##############

if not os.path.exists("user.db"):
    connection = sqlite3.connect("user.db")
    connection.execute(
        "create table USER(id INTEGER, name TEXT NOT NULL, email TEXT NOT NULL)")

displayRecord = False
dataInserted = False
peers = ["Node1", "Node2", "Node3", "Node4", "Node5"]


@app.route("/", methods=['GET', 'POST'])
def home():
    #isleader = raft_node.getLeader() == containerName
    if request.method == 'POST':
        # Extracting form data from the user
        name = request.form['name']
        id = request.form['id']
        email = request.form['email']

        #threading.Thread(target=listen, args=(UDP_Socket)).start()
        # time.sleep(0.01)
        # Inserting data into the db, one at a time
        insert_user_data(id, name, email)
        UDP_Socket.sendto(
            json.dumps({
                "sender_name": "client",
                "term": None,
                "method": "PUT",
                "request": "STORE",
                "key": id,
                "value": request.form}).encode(), (raft_node.getLeader(), 5555)
        )
        # Testing
        #print("fetching records...")
        # print(get_all_data())

        return render_template('form.html')
    #app.logger.info("=== rendering ====")
    return render_template('form.html', response=None)


@app.route("/fetch", methods=['POST'])
def fetchRecords():
    try:
        items = get_all_data()
        return render_template('form.html', items=items, displayRecord=True)
    except:
        items = ["Failure to fetch records"]


def insert_user_data(id: int, name: str, email: str):
    '''
    Inset values from the user form into db
    '''
    try:
        with sqlite3.connect("user.db") as transact:
            transact.cursor().execute(
                "INSERT into USER (id, name, email) values (?,?,?)", (id, name, email))
            transact.commit()
            dataInserted = True
        #app.logger.info(f"====  Data inserted in {containerName} DB  ====")
        return 0
    except:
        transact.rollback()
        print("Error in writing to db.")
        dataInserted = False
        return -1
    finally:
        transact.close()


def get_all_data():
    ''' 
    To fetch all records in the db
    '''
    try:
        #fetchCount += 1
        transact = sqlite3.connect('user.db')
        records = transact.execute("select * from USER")
        items = []
        for data in records:
            items.append({"id": data[0], "name": data[1], "email": data[2]})
        try:
            os.environ['totalDbRecords'] = str(len(items))
        except:
            pass
            #app.logger.info(f"OS totaldb error")
        return items
    except:
        print("Error in fetching the records.")
        return -1
    finally:
        # time.sleep(0.01)
        transact.close()
        UDP_Socket.sendto(
            json.dumps({
                "sender_name": "client",
                "term": None,
                "request": "STORE",
                "method": "GET",
                "key": fetchCount,
                "value": "select * from USER"}).encode(), (raft_node.getLeader(), 5555)
        )


def listen(skt):
    while True:
        try:
            msg, addr = skt.recvfrom(1024)
        except:
            app.logger.info(
                f"ERROR while fetching from socket : {traceback.print_exc()}"
            )

        # Decoding the Message received from Node 1
        if addr:
            decoded_msg = json.loads(msg.decode("utf-8"))
            app.logger.info(f"I am {os.environ['contName']}")
            app.logger.info(f"Message Received From : {addr}")
        time.sleep(2)


def main(UDP_Socket):
    for i in range(5):
        n = node()
        n.sendHeartBeat(UDP_Socket)
        app.logger.info(f"iteration {i}")


def incomingRequest(skt):
    while True:
        try:
            msg, addr = skt.recvfrom(1024)
            if addr:
                decoded_msg = json.loads(msg.decode("utf-8"))
            """if heartbeat_timeout:
                startelection
            elif heartbeat_received:
                reset_heartbeat_time"""
        except:
            app.logger.info(
                f"ERROR while fetching from socket : {traceback.print_exc()}"
            )

        # Decoding the Message received from Node 1
        if addr:
            decoded_msg = json.loads(msg.decode("utf-8"))
            app.logger.info(f"I am {os.environ['contName']}")
            app.logger.info(f"Message Received From : {addr}")
        time.sleep(0.1)


################   RAFT   ################


class node:
    def __init__(self, container, UDP_Socket):
        self.container = container
        self.term = int(os.environ['currentTerm'])
        self.status = "follower"
        self.DB = {}
        self.log = []
        self.entries = []
        self.peers = ["Node1", "Node2", "Node3", "Node4", "Node5"]
        self.confirmations = [False]*len(self.peers)
        self.nextIndex = {}
        self.matchIndex = {}
        self.commitIdx = 0
        self.staged = None
        self.timeout_thread = None
        self.majority = (len(self.peers) + 1) // 2
        self.voteCount = 0
        self.udpSocket = UDP_Socket
        #self.lock = threading.Lock()
        self.listenController = threading.Thread(target=self.treatController)
        # self.responseThread = threading.Thread(target=self.treatResponse)
        # self.listenHeartBeat = threading.Thread(target=self.treatHeartBeat)
        self.listenerThread = True
        self.voteReqThread = True
        self.heartBeatThread = True
        self.isTimeoutThread = True
        self.needResponse = True
        self.broadcastlog = False
        self.sendLogVal = False
        self.sendLogValTo = ""
        self.responseGot = {}
        self.listenController.start()
        # self.responseThread.start()
        # self.listenHeartBeat.start()
        app.logger.info(
            f"{self.container} - starting as follower, term {self.term}")
        self.initializeTimeout()
        # self.votelistener()

    def set_status(self):
        app.logger.info(f"---{self.container} set to leader ----")
        self.status = "leader"
        os.environ["votedFor"] = self.container
        self.startHeartBeat()

    def treatController(self):
        while self.listenerThread:
            res, origin = self.udpSocket.recvfrom(1024)
            self.responseGot = json.loads(res.decode("utf-8"))
            res = json.loads(res.decode("utf-8"))
            if res:
                # app.logger.info(f"---- Response received in {self.container} ----")
                self.needResponse = True

                # app.logger.info(self.responseGot)
                # and res['sender_name'] == 'Controller':
                if "sender_name" in res:
                    app.logger.info(
                        f"{os.environ['contName']} Received request from {res['sender_name']} for {res['request']}....."
                    )
                    if res["sender_name"] == "client":
                        if res["method"] == "PUT":
                            name = res["value"]['name']
                            id = res["value"]['id']
                            email = res["value"]['email']
                            insert_user_data(id, name, email)
                        if self.status == "leader":
                            self.handleStore(res)

                    elif res["request"] == "LEADER_INFO":
                        msg = {"key": "LEADER",
                               "value": os.environ["votedFor"]}
                        self.udpSocket.sendto(
                            json.dumps(msg).encode(), ("Controller", 5555)
                        )
                        app.logger.info(
                            f"Sending Leader info {msg} to controller from {os.environ['contName']}"
                        )

                    elif res["request"] == "CONVERT_FOLLOWER":
                        app.logger.info(
                            f"{os.environ['contName']} Converting to follower...."
                        )
                        self.status = "follower"
                        self.listenerThread = True
                        self.voteReqThread = True
                        self.heartBeatThread = True
                        self.isTimeoutThread = True
                        app.logger.info(
                            f"{os.environ['contName']} is now a follower.")
                        time.sleep(0.2)
                        self.startElection()

                    elif res["request"] == "TIMEOUT":
                        app.logger.info(
                            f"---- Timing out {os.environ['contName']} ----"
                        )
                        self.election_time = 0
                        app.logger.info(f"Timeout Done.")

                    elif res["request"] == "SHUTDOWN":
                        app.logger.info(
                            f"Shutting down all threads in the {os.environ['contName']}"
                        )
                        self.status = "follower"
                        self.listenerThread = False
                        self.voteReqThread = False
                        self.heartBeatThread = False
                        self.isTimeoutThread = False
                        app.logger.info(f"Shutdown completed.")

                    elif res["request"] == "RESTART":
                        self.listenerThread = True
                        self.voteReqThread = True
                        self.heartBeatThread = True
                        self.isTimeoutThread = True

                    elif res["request"] == "STORE":
                        if self.status == "leader":
                            self.handleStore(res)
                        else:
                            # sending back leader info
                            self.udpSocket.sendto(
                                json.dumps(
                                    {
                                        "sender_name": self.container,
                                        "term": None,
                                        "request": "LEADER_INFO",
                                        "key": "LEADER",
                                        "value": os.environ["votedFor"]
                                    }
                                ).encode(),
                                (res["sender_name"], 5555)
                            )

                    elif res["request"] == "RETRIEVE":
                        app.logger.info(
                            f"Retrieve requested in {self.container}")
                        if self.status == "leader":
                            log_entries = self.getLog(res)
                            self.udpSocket.sendto(
                                json.dumps(
                                    {
                                        "sender_name": self.container,
                                        "term": None,
                                        "request": "RETRIEVE",
                                        "key": "COMMITED_LOGS",
                                        "value": log_entries
                                    }
                                ).encode(),
                                (res["sender_name"], 5555)
                            )

                        else:
                            # sending back leader info
                            res_data = {
                                "sender_name": self.container,
                                "term": None,
                                "request": "LEADER_INFO",
                                "key": "LEADER",
                                "value": os.environ["votedFor"]
                            }
                            self.udpSocket.sendto(
                                json.dumps(res_data).encode(
                                ), (res["sender_name"], 5555)
                            )
                            app.logger.info(
                                f"Retrieve response {res_data} to controller from {os.environ['contName']}"
                            )
                    elif res["request"] == "GETLOG":
                        # For testing purpose
                        self.udpSocket.sendto(
                            json.dumps(
                                {
                                    "term": self.term,
                                    "sender_name": self.container,
                                    "logs": self.log,
                                }
                            ).encode(),
                            (res["sender_name"], 5555)
                        )
                    else:
                        self.listenerThread = True
                        self.voteReqThread = True
                        self.heartBeatThread = True
                        self.isTimeoutThread = True

                if "candidateId" in res:
                    # Vote Request
                    # app.logger.info(f"I'm {os.environ['contName']} - received vote request from {res['candidateId']}")

                    voting, _ = self.finalizeVote(res)  # , res["commitIdx"])
                    if voting:
                        os.environ["votedFor"] = res["candidateId"]

                        # Sending Vote Acknowledgement iff True
                        self.udpSocket.sendto(
                            json.dumps(
                                {
                                    "voteGranted": voting,
                                    "votedBy": self.container,
                                    "term": self.term,
                                }
                            ).encode(),
                            (res["candidateId"], 5555),
                        )
                    # app.logger.info(f"Voting from {os.environ['contName']} for {res['candidateId']} is {voting}")
                if "leaderId" in res:
                    # heartbeat
                    # app.logger.info("----Received heartbeat -----")
                    os.environ["votedFor"] = res["leaderId"]
                    self.resetTimeout()
                    term, success, info = self.followHeartBeat(res)
                    # Sending Vote Acknowledgement iff True
                    self.udpSocket.sendto(
                        json.dumps(
                            {
                                "term": term,
                                "success": success,
                                "info": info,
                                "from": self.container
                            }
                        ).encode(),
                        (res["leaderId"], 5555),
                    )
                    if "action" in res:
                        if res["action"] == "log":
                            time.sleep(0.05)
                            self.udpSocket.sendto(
                                json.dumps(
                                    {
                                        "term": term,
                                        "success": success,
                                        "from": os.environ["votedFor"]
                                    }
                                ).encode(),
                                ("Controller", 5555),
                            )

                if "success" in res:
                    if res['success']:
                        if res['term'] > self.term:
                            self.status = "follower"
                            return
                        if res["info"] == "SUCCESS" and self.broadcastlog:
                            try:
                                self.nextIndex[res['from']] += 1
                                self.matchIndex[res['from']] += 1
                            except:
                                pass
                            #app.logger.info(f"--- success returned - broadcastlog = {self.broadcastlog}")
                            node_num = int(res['from'][-1])
                            #app.logger.info(f"node_num = {node_num}")
                            #app.logger.info(f"self.confirmations = {self.confirmations}")
                            self.confirmations[node_num-1] = True

                    elif res['success'] == False:
                        if res['term'] > self.term:
                            self.status = "follower"

                        if 'info' in res:
                            if res['info'] == "Inconsistent":
                                app.logger.info(
                                    f"Log inconsistent in {res['from']}")
                                # send the inconsistent log to the follower in the next heartbeat
                                self.sendLogVal = True
                                self.sendLogValTo = res['from']

                elif "voteGranted" in res:
                    voted = res["voteGranted"]
                    # app.logger.info(f"RECEIVED VOTE {voted} from {res['votedBy']}")

                    if voted and self.status == "candidate":
                        self.addVote()
                    elif not voted:
                        term = res["term"]
                        if term > self.term:
                            self.term = term
                            os.environ['currentTerm'] = str(self.term)
                            self.status = "follower"
            else:
                self.needResponse = False
                self.responseGot = {}
            # time.sleep(0.04)

    def addVote(self):
        self.voteCount += 1
        if self.voteCount >= self.majority:
            app.logger.info(
                f"{self.container} is the new leader for the term {self.term}"
            )
            self.status = "leader"
            os.environ["votedFor"] = str(self.container)
            os.environ["currentTerm"] = str(self.term)

            for peer in self.peers:
                if peer != self.container:
                    self.nextIndex[peer] = int(self.commitIdx) + 0
                    self.matchIndex[peer] = 0

            self.startHeartBeat()

    def startHeartBeat(self):
        app.logger.info("Starting Heartbeat")
        for target in self.peers:
            if target != self.container:
                t = threading.Thread(target=self.sendHeartBeat, args=(target,))
                t.start()

    def startElection(self):
        self.term += 1
        os.environ['currentTerm'] = str(self.term)
        self.voteCount = 0
        app.logger.info(f"{self.container} becomes a Candidate")
        self.status = "candidate"
        isleader = False
        self.initializeTimeout()
        self.addVote()
        self.voteReqThreadStart()


    def sendHeartBeat(self, target):
        # Creating Socket and binding it to the target container IP and port
        # UDP_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

        # Bind the node to sender ip and port
        # UDP_Socket.bind((os.environ['contName'], 5555))
        # app.logger.info(f"--- sending heartbeat to {target}")

        while self.status == "leader" and self.heartBeatThread:
            isleader = True
            start = time.time()
            # for target in self.peers:
            try:
                lastlogterm = 0
                if len(self.log):
                    #app.logger.info(f"---- 368 Log {self.log[-1]} ----")
                    lastlogterm = self.log[-1]['term']
                msg = {
                    "term": self.term,
                    "leaderId": os.environ["contName"],
                    "entries": [],
                    "prevLogIndex": len(self.log)-1,
                    # int(os.environ['currentTerm'])-1
                    "prevLogTerm":  lastlogterm,
                    "leaderCommit": self.commitIdx
                }
                if self.sendLogVal and self.sendLogValTo == target:
                    app.logger.info(
                        f"--- fixing log inconsistencies in {target} ---")
                    msg["entries"] = self.log
                    msg["inconsistency"] = True
                    self.sendLogVal = False
                    self.sendLogValTo = ""
                else:
                    msg["entries"] = []

                self.udpSocket.sendto(json.dumps(msg).encode(), (target, 5555))
            except:
                pass
                # app.logger.info(
                #     f"---- {target} not available, could not send heartbeat ----")
            delta = time.time() - start

            # heartbeat every 100ms
            time.sleep(0.1)  # (200 - delta) / 1000)

        app.logger.info(
            f"{self.container} out of heartbeat.. stepping down.... ")

    def initializeTimeout(self):
        self.resetTimeout()
        if self.timeout_thread and self.timeout_thread.isAlive():
            return
        self.timeout_thread = threading.Thread(target=self.timeout)
        self.timeout_thread.start()

    def resetTimeout(self):
        # app.logger.info(f"--- Reset timeout --- {self.container}")
        # 1500 - 2500 ms
        self.election_time = time.time() + random.randrange(200, 210) / 100
        # app.logger.info(f"{self.election_time}")

    def timeout(self):
        # stop timeout after election win
        if self.status == "leader":
            self.startHeartBeat()
            app.logger.info(
                f"--- Leader {self.container} starting heartbeat ---")
        while self.status != "leader" and self.isTimeoutThread:
            delta = self.election_time - time.time()
            # app.logger.info(f"---delta value in {self.container} = {delta}")

            if delta < 0:
                app.logger.info(f"---- Timeout ----")
                app.logger.info(f"--- starting election by {self.container}")
                self.startElection()
            else:
                time.sleep(delta)
            # time.sleep(0.2)

    def voteReqThreadStart(self):
        for voter in self.peers:
            threading.Thread(target=self.requestVote,
                             args=(voter, self.term)).start()

    # request vote from other nodes

    def requestVote(self, voter, term):
        isleader = False
        lastlogterm = 0
        if len(self.log):
            #app.logger.info(f"---- Log {self.log[-1]} ----")
            lastlogterm = self.log[-1]['term']
        message = {
            "term": term,
            "candidateId": self.container,
            "commitIdx": self.commitIdx,
            "lastLogIndex": self.commitIdx,
            "lastLogTerm": lastlogterm,
        }
        app.logger.info(f"{os.environ['contName']} - requesting vote")
        # route = "vote_req"
        count = 0
        while (
            self.status == "candidate"
            and self.term == term
            and self.voteReqThread
            and count < 10
        ):
            # for target in self.peers:
            try:
                self.udpSocket.sendto(json.dumps(
                    message).encode(), (voter, 5555))
            except:
                pass
                # app.logger.info(
                #    f"---- {voter} not available, could not send heartbeat ----")
            count += 1
            time.sleep(0.02)
            # reply, addr = self.udpSocket.recvfrom(1024)
            # break

    def finalizeVote(self, req):
        lastLogTerm = 0
        if len(self.log):
            try:
                lastLogTerm = self.log[-1]['term']
            except:
                lastLogTerm = 0
        # app.logger.info(f"===== {req}")
        # app.logger.info(f"{lastLogTerm}")
        # app.logger.info(f"{req['lastLogTerm']}")
        if self.term < req["term"] and self.commitIdx <= req["commitIdx"] and lastLogTerm <= req["lastLogTerm"]:

            self.resetTimeout()
            self.term = req["term"]
            os.environ['currentTerm'] = str(self.term)
            os.environ['votedFor'] = str(req['candidateId'])
            return True, self.term
        else:
            return False, self.term

    def followHeartBeat(self, msg):
        term = int(msg["term"])

        if self.term > term:
            resmsg = f"My ({self.container}) term is {self.term} but yours ({msg['leaderId']}) is {msg['term']}"
            return self.term, False, resmsg

        elif self.term <= term:
            self.leader = msg["leaderId"]
            self.resetTimeout()

            if self.status == "leader":
                self.status = "follower"
                self.initializeTimeout()

            elif self.status == "candidate":
                self.status = "follower"

            if self.term < term:
                self.term = term
                os.environ['currentTerm'] = str(self.term)

        # if len(msg['entries']) == 0:
        #     # receivevd heartbeat
        #     return self.term, True, "heartbeat acknowledged"

        #app.logger.info("----- log consistency check -----")
        #incoming_entries = len(msg["entries"])
        prevLogIndex = int(msg['prevLogIndex'])
        prevLogTerm = int(msg['prevLogTerm'])
        indexPos = 0

        # for ind in range(len(self.log)):
        #     indexPos = ind
        #     if ind < prevLogIndex:
        #         continue
        #     if ind == prevLogIndex:
        #         if self.log[ind]['term'] != prevLogTerm:
        #             return self.term, False, "Inconsistent"

        if 'inconsistency' in msg:
            if msg['inconsistency']:
                #app.logger.info("--- inside inconsistency fix -----")
                # app.logger.info(msg['entries'])
                temp = 0
                for entry in msg['entries']:
                    temp += 1
                    # log may already retained values from persistent storage
                    if temp > len(self.log):
                        self.log.append(entry)

                # commiting values to db
                temp = 0
                for entry in self.log:
                    if 'id' in entry['value']:
                        temp += 1
                        if temp > int(os.environ['totalDbRecords']):
                            name = entry["value"]['name']
                            id = entry["value"]['id']
                            email = entry["value"]['email']
                            insert_user_data(id, name, email)

                os.environ['totalDbRecords'] = str(temp)
                commited = self.commitLog("")
                # if commited:
                #     app.logger.info(
                #         f"==== Log committed by the follower - {self.container} ====")
                # else:
                #     pass
                    #app.logger.info(f"==== Log commit failed - {self.container} ====")
                app.logger.info(f"-------- fixed log ---- {self.log}")
                try:
                    pass
                    #self.log = [dict(val) for val in set(tuple(item.items()) for item in self.log)]
                    #app.logger.info("---- duplicate removal success ----")
                except:
                    pass

        elif len(msg['entries']):
            self.log.append(msg['entries'][0])
            commited = self.commitLog("")
            # if commited:
            #     app.logger.info(
            #         f"==== Log committed by the follower - {self.container} ====")
            # else:
            #     #app.logger.info(f"==== Log commit failed - {self.container} ====")
            #     pass

        # if len(self.log) >= prevLogIndex+2:
        #     if int(self.log[prevLogIndex]['term']) != prevLogTerm:
        #         if len(msg['entries']):
        #             self.log.append(msg['entries'][0])

        if len(self.log) == 0 and prevLogIndex >= 0:
            return self.term, False, "Inconsistent"

        if len(self.log)-1 < prevLogIndex:
            return self.term, False, "Inconsistent"

        if (prevLogIndex >= 0) and (len(self.log)-1 == prevLogIndex):
            if int(self.log[prevLogIndex]['term']) != prevLogTerm:
                return self.term, False, "Inconsistent"

        self.commitIdx = msg['leaderCommit']
        self.lastApplied = len(self.log)

        os.environ['currentTerm'] = str(self.term)

        return self.term, True, "SUCCESS"

        #self.log = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in self.log)]

    def save_as_json(self, msg):
        self.DB[msg['key']] = msg['value']
        app.logger.info("------ save as json, DB value ------")
        app.logger.info(self.DB)

    def spread_update(self, peer, message):
        app.logger.info(f"Sending update from {self.container} to {peer}")
        # for node in self.peers:
        #     if node != self.container:
        #         self.udpSocket.sendto(
        #             json.dumps(
        #                 message)
        #             .encode(),
        #             (node, 5555))
        try:
            self.udpSocket.sendto(json.dumps(message).encode(), (peer, 5555))
        except:
            pass
            # app.logger.info(
            #    f"---- {peer} not available, could not send heartbeat ----")
        # if lock:
        #     lock.release()

    def handleStore(self, req):
        '''
            Controller STORE request handle
        '''
        isleader = True
        #app.logger.info(f"{self.container} handle put")
        # self.lock.acquire()
        waited = 0
        lastlogterm = 0
        if len(self.log):
            #app.logger.info(f"---- 565 Log {self.log[-1]} ----")
            lastlogterm = self.log[-1]['term']
        log_message = {
            "payload": req,
            "action": "log",
            "term": self.term,
            "leaderId": os.environ["contName"],
            "entries": [{
                'term': self.term,
                'key': req['key'],
                'value': req['value']
            }],
            "prevLogIndex": len(self.log)-1,
            # int(os.environ['currentTerm'])-1
            "prevLogTerm": lastlogterm,
            "leaderCommit": self.commitIdx
        }
        # self.entries =

        app.logger.info("------ Broadcasting log -------")
        # spread log  to all followers
        self.broadcastlog = True
        self.confirmations = [False] * len(self.peers)
        for peer in self.peers:
            if peer != self.container:
                threading.Thread(target=self.spread_update,
                                 args=(peer, log_message)).start()

        app.logger.info("---- Waiting for confirmations -----")
        # while sum(self.confirmations) + 1 < self.majority:
        #     waited += 0.0005
        #     time.sleep(0.0005)
        #     if waited > 1000 / 1000:
        #         print(f"waited 1000 ms, update rejected:")
        #         self.lock.release()
        #         return False

        # while True:
        #     if sum(self.confirmations) + 1 >= self.majority:
        #         break
        time.sleep(0.1)

        app.logger.info("---- Logs Replicated -----")
        self.log.append(log_message["entries"][0])
        self.commitIdx += 1
        self.confirmations = [False]*len(self.peers)
  
        self.broadcastlog = False

        if "method" in req:
            if req["method"] == "PUT":
                return True
        commited = self.commitLog(req)
        # if commited:
        #     app.logger.info(
        #         f"==== Log committed by the leader - {self.container} ====")
        # else:
        #     #app.logger.info(f"==== Log commit failed - {self.container} ====")
        #     pass
        return True

    def getLog(self, req):
        '''
            Controller RETRIEVE request handle
        '''
        return self.log

    def commitLog(self, req):
        '''
            Persisting the log in JSON file
        '''
        try:
            with open("log.json", "w") as log:
                json.dump(self.log, log)

            if req != "":
                if "value" in req:
                    name = req["value"]['name']
                    id = req["value"]['id']
                    email = req["value"]['email']
                    insert_user_data(id, name, email)

            return True
        except:
            return False

    def setLog(self, data):
        self.log = data

    def getLeader(self):
        return os.environ['votedFor']


if __name__ == "__main__":
    # Creating Socket and binding it to the target container IP and port
    UDP_Socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    app.logger.info(os.environ["contName"])
    # Bind the node to sender ip and port
    UDP_Socket.bind((os.environ["contName"], 5555))

    raft_node = node(os.environ["contName"], UDP_Socket)

    logFile = "log.json"
    if not os.path.exists(logFile):
        open(logFile, 'w')
    else:
        try:
            with open(logFile, 'r') as log:
                raft_node.setLog(json.load(log))
                app.logger.info(f"=== Persistent log found ===")
                # app.logger.info(f"{json.load(log)}")
                # app.logger.info(f"Reading the logs....")
                # logs = raft_node.getLog()

                # app.logger.info(f"=== Done. ===")
                # app.logger.info(f"{logs}")

                # try:
                #     app.logger.info(f"Last term = {logs[-1]['term']}")
                #     app.logger.info(f"Last log index = {len(logs)}")

                # except:
                #     pass
        except:
            pass
            #app.logger.info(f" == JSON load ERROR == ")

    fetchCount = 1000
    global isleader
    isleader = True
    """
    #Starting thread 1
    listening_thread = threading.Thread(target=incomingRequest, args=[UDP_Socket])
    listening_thread.start()
    time.sleep(0.05)
    heartbeat_thread = threading.Thread(target=sendHeartBeat, args=[UDP_Socket])
    heartbeat_thread.start()
    time.sleep(0.05)
    """

    # if os.environ['contName'] == 'Node1':
    # main(UDP_Socket)

    if containerName == "Node1":
        # raft_node.set_status()
        PORT = "5000"
    elif containerName == "Node2":
        PORT = "5001"
    elif containerName == "Node3":
        PORT = "5002"
    elif containerName == "Node4":
        PORT = "5003"
    elif containerName == "Node5":
        PORT = "5004"
    else:
        PORT = "5006"

    app.run(host="0.0.0.0", port=PORT)
