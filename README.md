<div align="justify">

# RAFT Consensus Algorithm Implementation
### Distributed System Course Project

## Introduction
This project focuses on the implementation of the RAFT consensus algorithm in a distributed system. The journey began with a simple web application based on the client-server architecture, which was expanded to run on multiple containers, forming a distributed system. The core of the project lies in its two key phases:

### Leader Election
In this phase, the leader election part of the RAFT consensus algorithm was implemented and validated using remote procedure calls (RPCs) from the controller in the Docker container.

### Log Replication
This phase continued with the implementation of safe log replication combined with leader election. The primary goal was to ensure data consistency and fault tolerance in the distributed system.

## Architecture Overview
The system's architecture comprises five nodes, a controller, and a client. Every node has the same methods and RPCs implementation. Based on the RAFT consensus algorithm, one node acts as the leader, while the others remain as followers. The STORE/RETRIEVE requests from the client or controller are exclusively served by the leader.


## Implementation Details

### Leader Election
Upon container initiation, all nodes begin as followers. An election is triggered when any node times out, which is set at four times the heartbeat duration (200ms). The candidate node broadcasts a JSON message through the RequestVote RPC. Other nodes evaluate the term number and perform a safety check on logs before casting their votes. The heartbeat, an append-entry RPC with an empty JSON message, persists every 200ms until another node's timeout triggers a new election.

### Log Replication
Store requests received by the leader from the controller or client are appended to each node's log. Once a majority commits the entry, the leader finalizes it. The RAFT algorithm ensures consistent and safe log replication, making the system reliable and fault-tolerant. Append entry RPCs handle log replication, also doubling as heartbeats.

## Validation
The system's resilience and functionality were tested through various scenarios using the controller in the Docker container and a client. The system was proven to be fault-tolerant and error-free under multiple test conditions, including node restarts, leader shutdowns, and subsequent log replications.

## More on Leader Election
Each of the five nodes in the architecture has the same implementation of methods and RPCs. Using the RAFT algorithm, one node becomes a leader at any given time. Nodes start as followers, with a timeout set at four times the heartbeat duration (200ms). If a leader fails to send a heartbeat, a follower assumes leader failure, triggering a new election. This self-correcting mechanism ensures the system remains fault-tolerant.

## Demo
Refer [Demo_video.mp4](Demo_video.mp4)

</div>
