# -*- coding: utf-8 -*-
#application_key = 4f068b5c0c34ac675906bc61e0eed95e
from neb.plugins import Plugin, admin_only
from neb.engine import KeyValueStore, RoomContextStore

import json
import urlparse

import logging as log

class TrelloPlugin(Plugin):
	"""Plugin for interacting with Trello. Whenever a new card
	is inserted or any new notification is recieved related to 
	a board, the message is published in all the rooms. 
	"""

	name = "trello"

	#Webhooks:
    #    /neb/trello

    TRACKING = ["track", "tracking"]
    TYPE_TRACK = "org.matrix.neb.plugin.trello.projects.tracking"

    def __init__(self, *args, **kwargs):
        super(TrelloPlugin, self).__init__(*args, **kwargs)
        self.store = KeyValueStore("trello.json")
        self.rooms = RoomContextStore(
            [TrelloPlugin.TYPE_TRACK]
        )

        if not self.store.has("known_projects"):
            self.store.set("known_projects", [])

        if not self.store.has("secret_token"):
            self.store.set("secret_token", "")


    def on_event(self, event, event_type):
        self.rooms.update(event)

    def on_sync(self, sync):
        log.debug("Plugin: Trello sync state:")
        self.rooms.init_from_sync(sync)

    def get_webhook_key(self):
        return "trello"


    def send_message_to_repos(self, repo, push_message):
        # send messages to all rooms registered with this project.
        for room_id in self.rooms.get_room_ids():
            try:
                if repo in self.rooms.get_content(room_id, TrelloPlugin.TYPE_TRACK)["projects"]:
                    self.matrix.send_message_event(
                        room_id,
                        "m.room.message",
                        self.matrix.get_html_body(push_message, msgtype="m.notice")
                    )
            except KeyError:
                pass


    def on_revieve_vote_on_card(self, data):
    	card = data["action"]["data"]["card"]["name"]
    	board = data["action"]["data"]["board"]["name"]

    	msg = '<font color="red"> <b>%s</b> card on <b> %s </b> board got upvoted </font>'

    	self.send_message_to_repos(name, msg) 



    def on_receive_webhook(self, url, data, ip, headers):
    	if self.store.get("secret_token"):
            token_sha1 = headers.get('X-Trello-Webhook')
            payload_body = data
            calc = hmac.new(str(self.store.get("secret_token")), payload_body,
                            sha1)
            calc_sha1 = "sha1=" + calc.hexdigest()
            if token_sha1 != calc_sha1:
                log.warn("TrelloServer: FAILED SECRET TOKEN AUTH. IP=%s",
                         ip)
                return ("", 403, {})

      	json_data = json.loads(data)
      	name = json_data["action"]["data"]["board"]["name"]
      	action_type = json_data["action"]["type"]

      	if name not in self.store.get("known_projects"):
      		log.info("Added new Board: %s", name)
            projects = self.store.get("known_projects")
            projects.append(name)
            self.store.set("known_projects", projects)

        if action_type == 'voteOnCard':
        	self.on_revieve_vote_on_card(json_data)

