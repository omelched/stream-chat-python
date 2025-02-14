import sys
from operator import itemgetter
from contextlib import suppress

import jwt
import pytest
import time
import uuid
from stream_chat import StreamChat
from stream_chat.base.exceptions import StreamAPIException


class TestClient(object):
    def test_normalize_sort(self, client):
        expected = [
            {"field": "field1", "direction": 1},
            {"field": "field2", "direction": -1},
        ]
        actual = client.normalize_sort([{"field1": 1}, {"field2": -1}])
        assert actual == expected
        actual = client.normalize_sort(
            [{"field": "field1", "direction": 1}, {"field": "field2", "direction": -1}]
        )
        assert actual == expected
        actual = client.normalize_sort({"field1": 1})
        assert actual == [{"field": "field1", "direction": 1}]
        # The following example is not recommended because the order of the fields is not guaranteed in Python < 3.7
        actual = client.normalize_sort({"field1": 1, "field2": -1})
        if sys.version_info >= (3, 7):
            assert actual == expected
        else:
            # Compare elements regardless of the order
            assert sorted(actual, key=itemgetter("field")) == expected

    def test_mute_user(self, client, random_users):
        response = client.mute_user(random_users[0]["id"], random_users[1]["id"])
        assert "mute" in response
        assert "expires" not in response["mute"]
        assert response["mute"]["target"]["id"] == random_users[0]["id"]
        assert response["mute"]["user"]["id"] == random_users[1]["id"]
        client.unmute_user(random_users[0]["id"], random_users[1]["id"])

    def test_mute_user_with_timeout(self, client, random_users):
        response = client.mute_user(
            random_users[0]["id"], random_users[1]["id"], timeout=10
        )
        assert "mute" in response
        assert "expires" in response["mute"]
        assert response["mute"]["target"]["id"] == random_users[0]["id"]
        assert response["mute"]["user"]["id"] == random_users[1]["id"]
        client.unmute_user(random_users[0]["id"], random_users[1]["id"])

    def test_get_message(self, client, channel, random_user):
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        client.delete_message(msg_id)
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        message = client.get_message(msg_id)
        assert message["message"]["id"] == msg_id

    def test_auth_exception(self):
        client = StreamChat(api_key="bad", api_secret="guy")
        with pytest.raises(StreamAPIException):
            client.get_channel_type("team")

    def test_get_channel_types(self, client):
        response = client.get_channel_type("team")
        assert "permissions" in response

    def test_list_channel_types(self, client):
        response = client.list_channel_types()
        assert "channel_types" in response

    def test_update_channel_type(self, client):
        response = client.update_channel_type("team", commands=["ban", "unban"])
        assert "commands" in response
        assert response["commands"] == ["ban", "unban"]

    def test_get_command(self, client, command):
        response = client.get_command(command["name"])
        assert command["name"] == response["name"]

    def test_update_command(self, client, command):
        response = client.update_command(command["name"], description="My new command")
        assert "command" in response
        assert "My new command" == response["command"]["description"]

    def test_list_commands(self, client):
        response = client.list_commands()
        assert "commands" in response

    def test_create_token(self, client):
        token = client.create_token("tommaso")
        assert type(token) is str
        payload = jwt.decode(token, client.api_secret, algorithms=["HS256"])
        assert payload.get("user_id") == "tommaso"

    def test_get_app_settings(self, client):
        configs = client.get_app_settings()
        assert "app" in configs

    def test_update_user(self, client):
        user = {"id": str(uuid.uuid4())}
        response = client.update_user(user)
        assert "users" in response
        assert user["id"] in response["users"]

    def test_update_users(self, client):
        user = {"id": str(uuid.uuid4())}
        response = client.update_users([user])
        assert "users" in response
        assert user["id"] in response["users"]

    def test_update_user_partial(self, client):
        user_id = str(uuid.uuid4())
        client.update_user({"id": user_id, "field": "value"})

        response = client.update_user_partial(
            {"id": user_id, "set": {"field": "updated"}}
        )

        assert "users" in response
        assert user_id in response["users"]
        assert response["users"][user_id]["field"] == "updated"

    def test_delete_user(self, client, random_user):
        response = client.delete_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]

    def test_deactivate_user(self, client, random_user):
        response = client.deactivate_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]

    def test_reactivate_user(self, client, random_user):
        response = client.deactivate_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]
        response = client.reactivate_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]

    def test_export_user(self, client, fellowship_of_the_ring):
        response = client.export_user("gandalf")
        assert "user" in response
        assert response["user"]["name"] == "Gandalf the Grey"

    def test_ban_user(self, client, random_user, server_user):
        client.ban_user(random_user["id"], user_id=server_user["id"])

    def test_unban_user(self, client, random_user, server_user):
        client.ban_user(random_user["id"], user_id=server_user["id"])
        client.unban_user(random_user["id"], user_id=server_user["id"])

    def test_flag_user(self, client, random_user, server_user):
        client.flag_user(random_user["id"], user_id=server_user["id"])

    def test_unflag_user(self, client, random_user, server_user):
        client.flag_user(random_user["id"], user_id=server_user["id"])
        client.unflag_user(random_user["id"], user_id=server_user["id"])

    def test_mark_all_read(self, client, random_user):
        client.mark_all_read(random_user["id"])

    def test_update_message(self, client, channel, random_user):
        msg_id = str(uuid.uuid4())
        response = channel.send_message(
            {"id": msg_id, "text": "hello world"}, random_user["id"]
        )
        assert response["message"]["text"] == "hello world"
        client.update_message(
            {
                "id": msg_id,
                "awesome": True,
                "text": "helloworld",
                "user": {"id": response["message"]["user"]["id"]},
            }
        )

    def test_delete_message(self, client, channel, random_user):
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        client.delete_message(msg_id)
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        client.delete_message(msg_id, hard=True)

    def test_flag_message(self, client, channel, random_user, server_user):
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        client.flag_message(msg_id, user_id=server_user["id"])

    def test_query_message_flags(self, client, channel, random_user, server_user):
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        client.flag_message(msg_id, user_id=server_user["id"])
        response = client.query_message_flags({"channel_cid": channel.cid})
        assert len(response["flags"]) == 1
        response = client.query_message_flags({"user_id": {"$in": [random_user["id"]]}})
        assert len(response["flags"]) == 1

    def test_unflag_message(self, client, channel, random_user, server_user):
        msg_id = str(uuid.uuid4())
        channel.send_message({"id": msg_id, "text": "helloworld"}, random_user["id"])
        client.flag_message(msg_id, user_id=server_user["id"])
        client.unflag_message(msg_id, user_id=server_user["id"])

    def test_query_users_young_hobbits(self, client, fellowship_of_the_ring):
        response = client.query_users({"race": {"$eq": "Hobbit"}}, {"age": -1})
        assert len(response["users"]) == 4
        assert [50, 38, 36, 28] == [u["age"] for u in response["users"]]

    def test_devices(self, client, random_user):
        response = client.get_devices(random_user["id"])
        assert "devices" in response
        assert len(response["devices"]) == 0

        client.add_device(str(uuid.uuid4()), "apn", random_user["id"])
        response = client.get_devices(random_user["id"])
        assert len(response["devices"]) == 1

        client.delete_device(response["devices"][0]["id"], random_user["id"])
        client.add_device(str(uuid.uuid4()), "apn", random_user["id"])
        response = client.get_devices(random_user["id"])
        assert len(response["devices"]) == 1

    def test_get_rate_limits(self, client):
        response = client.get_rate_limits()
        assert "server_side" in response
        assert "android" in response
        assert "ios" in response
        assert "web" in response

        response = client.get_rate_limits(server_side=True, android=True)
        assert "server_side" in response
        assert "android" in response
        assert "ios" not in response
        assert "web" not in response

        response = client.get_rate_limits(
            server_side=True, android=True, endpoints=["GetRateLimits", "SendMessage"]
        )
        assert "server_side" in response
        assert "android" in response
        assert "ios" not in response
        assert "web" not in response
        assert len(response["android"]) == 2
        assert len(response["server_side"]) == 2
        assert (
            response["android"]["GetRateLimits"]["limit"]
            == response["android"]["GetRateLimits"]["remaining"]
        )
        assert (
            response["server_side"]["GetRateLimits"]["limit"]
            > response["server_side"]["GetRateLimits"]["remaining"]
        )

    @pytest.mark.xfail
    def test_search_with_sort(self, client, channel, random_user):
        text = str(uuid.uuid4())
        ids = ["0" + text, "1" + text]
        channel.send_message(
            {"text": text, "id": ids[0]},
            random_user["id"],
        )
        channel.send_message(
            {"text": text, "id": ids[1]},
            random_user["id"],
        )
        response = client.search(
            {"type": "messaging"}, text, **{"limit": 1, "sort": [{"created_at": -1}]}
        )
        # searches all channels so make sure at least one is found
        assert len(response["results"]) >= 1
        assert response["next"] is not None
        assert ids[1] == response["results"][0]["message"]["id"]
        response = client.search(
            {"type": "messaging"}, text, **{"limit": 1, "next": response["next"]}
        )
        assert len(response["results"]) >= 1
        assert response["previous"] is not None
        assert response["next"] is None
        assert ids[0] == response["results"][0]["message"]["id"]

    def test_search(self, client, channel, random_user):
        query = "supercalifragilisticexpialidocious"
        channel.send_message(
            {"text": f"How many syllables are there in {query}?"},
            random_user["id"],
        )
        channel.send_message(
            {"text": "Does 'cious' count as one or two?"}, random_user["id"]
        )
        response = client.search(
            {"type": "messaging"}, query, **{"limit": 2, "offset": 0}
        )
        # searches all channels so make sure at least one is found
        assert len(response["results"]) >= 1
        assert query in response["results"][0]["message"]["text"]
        response = client.search(
            {"type": "messaging"}, "cious", **{"limit": 12, "offset": 0}
        )
        for message in response["results"]:
            assert query not in message["message"]["text"]

    def test_search_message_filters(self, client, channel, random_user):
        query = "supercalifragilisticexpialidocious"
        channel.send_message(
            {"text": f"How many syllables are there in {query}?"},
            random_user["id"],
        )
        channel.send_message(
            {"text": "Does 'cious' count as one or two?"}, random_user["id"]
        )
        response = client.search(
            {"type": "messaging"},
            {"text": {"$q": query}},
            **{
                "limit": 2,
                "offset": 0,
            },
        )
        assert len(response["results"]) >= 1
        assert query in response["results"][0]["message"]["text"]

    def test_search_offset_with_sort(self, client):
        query = "supercalifragilisticexpialidocious"
        with pytest.raises(ValueError):
            client.search(
                {"type": "messaging"},
                query,
                **{"limit": 2, "offset": 1, "sort": [{"created_at": -1}]},
            )

    def test_search_offset_with_next(self, client):
        query = "supercalifragilisticexpialidocious"
        with pytest.raises(ValueError):
            client.search(
                {"type": "messaging"}, query, **{"limit": 2, "offset": 1, "next": query}
            )

    def test_query_channels_members_in(self, client, fellowship_of_the_ring):
        response = client.query_channels({"members": {"$in": ["gimli"]}}, {"id": 1})
        assert len(response["channels"]) == 1
        assert response["channels"][0]["channel"]["id"] == "fellowship-of-the-ring"
        assert len(response["channels"][0]["members"]) == 9

    def test_create_blocklist(self, client):
        client.create_blocklist(name="Foo", words=["fudge", "heck"])

    def test_list_blocklists(self, client):
        response = client.list_blocklists()
        assert len(response["blocklists"]) == 2
        blocklist_names = {blocklist["name"] for blocklist in response["blocklists"]}
        assert "Foo" in blocklist_names

    def test_get_blocklist(self, client):
        response = client.get_blocklist("Foo")
        assert response["blocklist"]["name"] == "Foo"
        assert response["blocklist"]["words"] == ["fudge", "heck"]

    def test_update_blocklist(self, client):
        client.update_blocklist("Foo", words=["dang"])
        response = client.get_blocklist("Foo")
        assert response["blocklist"]["words"] == ["dang"]

    def test_delete_blocklist(self, client):
        client.delete_blocklist("Foo")

    def test_check_sqs(self, client):
        response = client.check_sqs("key", "secret", "https://foo.com/bar")
        assert response["status"] == "error"
        assert "invalid SQS url" in response["error"]

    @pytest.mark.skip(reason="slow and flaky due to waits")
    def test_custom_permission_and_roles(self, client):
        id, role = "my-custom-permission", "god"

        def wait():
            time.sleep(3)

        with suppress(Exception):
            client.delete_permission(id)
            wait()
        with suppress(Exception):
            client.delete_role(role)
            wait()

        custom = {
            "id": id,
            "name": "My Custom Permission",
            "action": "DeleteChannel",
            "owner": False,
            "same_team": True,
        }

        client.create_permission(custom)
        wait()
        response = client.get_permission(id)
        assert response["permission"]["id"] == id
        assert response["permission"]["custom"]
        assert not response["permission"]["owner"]
        assert response["permission"]["action"] == custom["action"]

        custom["owner"] = True
        client.update_permission(id, custom)

        wait()
        response = client.get_permission(id)
        assert response["permission"]["id"] == id
        assert response["permission"]["custom"]
        assert response["permission"]["owner"]
        assert response["permission"]["action"] == custom["action"]

        response = client.list_permissions()
        original_len = len(response["permissions"])
        assert response["permissions"][0]["id"] == id
        client.delete_permission(id)
        wait()
        response = client.list_permissions()
        assert len(response["permissions"]) == original_len - 1

        client.create_role(role)
        wait()
        response = client.list_roles()
        assert role in response["roles"]
        client.delete_role(role)
        wait()
        response = client.list_roles()
        assert role not in response["roles"]
