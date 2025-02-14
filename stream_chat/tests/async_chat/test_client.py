import sys
from contextlib import suppress
from operator import itemgetter

import jwt
import pytest
import time
import uuid
from stream_chat.async_chat import StreamChatAsync
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

    @pytest.mark.asyncio
    async def test_mute_user(self, event_loop, client, random_users):
        response = await client.mute_user(random_users[0]["id"], random_users[1]["id"])
        assert "mute" in response
        assert "expires" not in response["mute"]
        assert response["mute"]["target"]["id"] == random_users[0]["id"]
        assert response["mute"]["user"]["id"] == random_users[1]["id"]
        await client.unmute_user(random_users[0]["id"], random_users[1]["id"])

    @pytest.mark.asyncio
    async def test_mute_user_with_timeout(self, event_loop, client, random_users):
        response = await client.mute_user(
            random_users[0]["id"], random_users[1]["id"], timeout=10
        )
        assert "mute" in response
        assert "expires" in response["mute"]
        assert response["mute"]["target"]["id"] == random_users[0]["id"]
        assert response["mute"]["user"]["id"] == random_users[1]["id"]
        await client.unmute_user(random_users[0]["id"], random_users[1]["id"])

    @pytest.mark.asyncio
    async def test_get_message(self, event_loop, client, channel, random_user):
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        await client.delete_message(msg_id)
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        message = await client.get_message(msg_id)
        assert message["message"]["id"] == msg_id

    @pytest.mark.asyncio
    async def test_auth_exception(self):
        async with StreamChatAsync(api_key="bad", api_secret="guy") as client:
            with pytest.raises(StreamAPIException):
                await client.get_channel_type("team")

    @pytest.mark.asyncio
    async def test_get_channel_types(self, event_loop, client):
        response = await client.get_channel_type("team")
        assert "permissions" in response

    @pytest.mark.asyncio
    async def test_list_channel_types(self, event_loop, client):
        response = await client.list_channel_types()
        assert "channel_types" in response

    @pytest.mark.asyncio
    async def test_update_channel_type(self, event_loop, client):
        response = await client.update_channel_type("team", commands=["ban", "unban"])
        assert "commands" in response
        assert response["commands"] == ["ban", "unban"]

    @pytest.mark.asyncio
    async def test_get_command(self, client, event_loop, command):
        response = await client.get_command(command["name"])
        assert command["name"] == response["name"]

    @pytest.mark.asyncio
    async def test_update_command(self, client, event_loop, command):
        response = await client.update_command(
            command["name"], description="My new command"
        )
        assert "command" in response
        assert "My new command" == response["command"]["description"]

    @pytest.mark.asyncio
    async def test_list_commands(self, event_loop, client):
        response = await client.list_commands()
        assert "commands" in response

    def test_create_token(self, event_loop, client):
        token = client.create_token("tommaso")
        assert type(token) is str
        payload = jwt.decode(token, client.api_secret, algorithms=["HS256"])
        assert payload.get("user_id") == "tommaso"

    @pytest.mark.asyncio
    async def test_get_app_settings(self, event_loop, client):
        configs = await client.get_app_settings()
        assert "app" in configs

    @pytest.mark.asyncio
    async def test_update_user(self, event_loop, client):
        user = {"id": str(uuid.uuid4())}
        response = await client.update_user(user)
        assert "users" in response
        assert user["id"] in response["users"]

    @pytest.mark.asyncio
    async def test_update_users(self, event_loop, client):
        user = {"id": str(uuid.uuid4())}
        response = await client.update_users([user])
        assert "users" in response
        assert user["id"] in response["users"]

    @pytest.mark.asyncio
    async def test_update_user_partial(self, event_loop, client):
        user_id = str(uuid.uuid4())
        await client.update_user({"id": user_id, "field": "value"})

        response = await client.update_user_partial(
            {"id": user_id, "set": {"field": "updated"}}
        )

        assert "users" in response
        assert user_id in response["users"]
        assert response["users"][user_id]["field"] == "updated"

    @pytest.mark.asyncio
    async def test_delete_user(self, event_loop, client, random_user):
        response = await client.delete_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]

    @pytest.mark.asyncio
    async def test_deactivate_user(self, event_loop, client, random_user):
        response = await client.deactivate_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]

    @pytest.mark.asyncio
    async def test_reactivate_user(self, event_loop, client, random_user):
        response = await client.deactivate_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]
        response = await client.reactivate_user(random_user["id"])
        assert "user" in response
        assert random_user["id"] == response["user"]["id"]

    @pytest.mark.asyncio
    async def test_export_user(self, event_loop, client, fellowship_of_the_ring):
        response = await client.export_user("gandalf")
        assert "user" in response
        assert response["user"]["name"] == "Gandalf the Grey"

    @pytest.mark.asyncio
    async def test_ban_user(self, event_loop, client, random_user, server_user):
        await client.ban_user(random_user["id"], user_id=server_user["id"])

    @pytest.mark.asyncio
    async def test_unban_user(self, event_loop, client, random_user, server_user):
        await client.ban_user(random_user["id"], user_id=server_user["id"])
        await client.unban_user(random_user["id"], user_id=server_user["id"])

    @pytest.mark.asyncio
    async def test_flag_user(self, event_loop, client, random_user, server_user):
        await client.flag_user(random_user["id"], user_id=server_user["id"])

    @pytest.mark.asyncio
    async def test_unflag_user(self, event_loop, client, random_user, server_user):
        await client.flag_user(random_user["id"], user_id=server_user["id"])
        await client.unflag_user(random_user["id"], user_id=server_user["id"])

    @pytest.mark.asyncio
    async def test_mark_all_read(self, event_loop, client, random_user):
        await client.mark_all_read(random_user["id"])

    @pytest.mark.asyncio
    async def test_update_message(self, event_loop, client, channel, random_user):
        msg_id = str(uuid.uuid4())
        response = await channel.send_message(
            {"id": msg_id, "text": "hello world"}, random_user["id"]
        )
        assert response["message"]["text"] == "hello world"
        await client.update_message(
            {
                "id": msg_id,
                "awesome": True,
                "text": "helloworld",
                "user": {"id": response["message"]["user"]["id"]},
            }
        )

    @pytest.mark.asyncio
    async def test_delete_message(self, event_loop, client, channel, random_user):
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        await client.delete_message(msg_id)
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        await client.delete_message(msg_id, hard=True)

    @pytest.mark.asyncio
    async def test_flag_message(
        self, event_loop, client, channel, random_user, server_user
    ):
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        await client.flag_message(msg_id, user_id=server_user["id"])

    @pytest.mark.asyncio
    async def test_query_message_flags(
        self, event_loop, client, channel, random_user, server_user
    ):
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        await client.flag_message(msg_id, user_id=server_user["id"])
        response = await client.query_message_flags({"channel_cid": channel.cid})
        assert len(response["flags"]) == 1
        response = await client.query_message_flags(
            {"user_id": {"$in": [random_user["id"]]}}
        )
        assert len(response["flags"]) == 1

    @pytest.mark.asyncio
    async def test_unflag_message(
        self, event_loop, client, channel, random_user, server_user
    ):
        msg_id = str(uuid.uuid4())
        await channel.send_message(
            {"id": msg_id, "text": "helloworld"}, random_user["id"]
        )
        await client.flag_message(msg_id, user_id=server_user["id"])
        await client.unflag_message(msg_id, user_id=server_user["id"])

    @pytest.mark.asyncio
    async def test_query_users_young_hobbits(
        self, event_loop, client, fellowship_of_the_ring
    ):
        response = await client.query_users({"race": {"$eq": "Hobbit"}}, {"age": -1})
        assert len(response["users"]) == 4
        assert [50, 38, 36, 28] == [u["age"] for u in response["users"]]

    @pytest.mark.asyncio
    async def test_devices(self, event_loop, client, random_user):
        response = await client.get_devices(random_user["id"])
        assert "devices" in response
        assert len(response["devices"]) == 0

        await client.add_device(str(uuid.uuid4()), "apn", random_user["id"])
        response = await client.get_devices(random_user["id"])
        assert len(response["devices"]) == 1

        await client.delete_device(response["devices"][0]["id"], random_user["id"])
        await client.add_device(str(uuid.uuid4()), "apn", random_user["id"])
        response = await client.get_devices(random_user["id"])
        assert len(response["devices"]) == 1

    @pytest.mark.asyncio
    async def test_get_rate_limits(self, event_loop, client):
        response = await client.get_rate_limits()
        assert "server_side" in response
        assert "android" in response
        assert "ios" in response
        assert "web" in response

        response = await client.get_rate_limits(server_side=True, android=True)
        assert "server_side" in response
        assert "android" in response
        assert "ios" not in response
        assert "web" not in response

        response = await client.get_rate_limits(
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
    @pytest.mark.asyncio
    async def test_search_with_sort(self, client, channel, random_user):
        text = str(uuid.uuid4())
        ids = ["0" + text, "1" + text]
        await channel.send_message(
            {"text": text, "id": ids[0]},
            random_user["id"],
        )
        await channel.send_message(
            {"text": text, "id": ids[1]},
            random_user["id"],
        )
        response = await client.search(
            {"type": "messaging"}, text, **{"limit": 1, "sort": [{"created_at": -1}]}
        )
        # searches all channels so make sure at least one is found
        assert len(response["results"]) >= 1
        assert response["next"] is not None
        assert ids[1] == response["results"][0]["message"]["id"]
        response = await client.search(
            {"type": "messaging"}, text, **{"limit": 1, "next": response["next"]}
        )
        assert len(response["results"]) >= 1
        assert response["previous"] is not None
        assert response["next"] is None
        assert ids[0] == response["results"][0]["message"]["id"]

    @pytest.mark.asyncio
    async def test_search(self, client, channel, random_user):
        query = "supercalifragilisticexpialidocious"
        await channel.send_message(
            {"text": f"How many syllables are there in {query}?"},
            random_user["id"],
        )
        await channel.send_message(
            {"text": "Does 'cious' count as one or two?"}, random_user["id"]
        )
        response = await client.search(
            {"type": "messaging"}, query, **{"limit": 2, "offset": 0}
        )
        # searches all channels so make sure at least one is found
        assert len(response["results"]) >= 1
        assert query in response["results"][0]["message"]["text"]
        response = await client.search(
            {"type": "messaging"}, "cious", **{"limit": 12, "offset": 0}
        )
        for message in response["results"]:
            assert query not in message["message"]["text"]

    @pytest.mark.asyncio
    async def test_search_message_filters(self, client, channel, random_user):
        query = "supercalifragilisticexpialidocious"
        await channel.send_message(
            {"text": f"How many syllables are there in {query}?"},
            random_user["id"],
        )
        await channel.send_message(
            {"text": "Does 'cious' count as one or two?"}, random_user["id"]
        )
        response = await client.search(
            {"type": "messaging"},
            {"text": {"$q": query}},
            **{
                "limit": 2,
                "offset": 0,
            },
        )
        assert len(response["results"]) >= 1
        assert query in response["results"][0]["message"]["text"]

    @pytest.mark.asyncio
    async def test_search_offset_with_sort(self, client):
        query = "supercalifragilisticexpialidocious"
        with pytest.raises(ValueError):
            await client.search(
                {"type": "messaging"},
                query,
                **{"limit": 2, "offset": 1, "sort": [{"created_at": -1}]},
            )

    @pytest.mark.asyncio
    async def test_search_offset_with_next(self, client):
        query = "supercalifragilisticexpialidocious"
        with pytest.raises(ValueError):
            await client.search(
                {"type": "messaging"}, query, **{"limit": 2, "offset": 1, "next": query}
            )

    @pytest.mark.asyncio
    async def test_query_channels_members_in(
        self, event_loop, client, fellowship_of_the_ring
    ):
        response = await client.query_channels(
            {"members": {"$in": ["gimli"]}}, {"id": 1}
        )
        assert len(response["channels"]) == 1
        assert response["channels"][0]["channel"]["id"] == "fellowship-of-the-ring"
        assert len(response["channels"][0]["members"]) == 9

    @pytest.mark.asyncio
    async def test_create_blocklist(self, event_loop, client):
        await client.create_blocklist(name="Foo", words=["fudge", "heck"])

    @pytest.mark.asyncio
    async def test_list_blocklists(self, event_loop, client):
        response = await client.list_blocklists()
        assert len(response["blocklists"]) == 2
        blocklist_names = {blocklist["name"] for blocklist in response["blocklists"]}
        assert "Foo" in blocklist_names

    @pytest.mark.asyncio
    async def test_get_blocklist(self, event_loop, client):
        response = await client.get_blocklist("Foo")
        assert response["blocklist"]["name"] == "Foo"
        assert response["blocklist"]["words"] == ["fudge", "heck"]

    @pytest.mark.asyncio
    async def test_update_blocklist(self, event_loop, client):
        await client.update_blocklist("Foo", words=["dang"])
        response = await client.get_blocklist("Foo")
        assert response["blocklist"]["words"] == ["dang"]

    @pytest.mark.asyncio
    async def test_delete_blocklist(self, event_loop, client):
        await client.delete_blocklist("Foo")

    @pytest.mark.asyncio
    async def test_check_sqs(self, client):
        response = await client.check_sqs("key", "secret", "https://foo.com/bar")
        assert response["status"] == "error"
        assert "invalid SQS url" in response["error"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="slow and flaky due to waits")
    async def test_custom_permission_and_roles(self, client):
        id, role = "my-custom-permission", "god"

        def wait():
            time.sleep(3)

        with suppress(Exception):
            await client.delete_permission(id)
            wait()
        with suppress(Exception):
            await client.delete_role(role)
            wait()

        custom = {
            "id": id,
            "name": "My Custom Permission",
            "action": "DeleteChannel",
            "owner": False,
            "same_team": True,
        }

        await client.create_permission(custom)
        wait()
        response = await client.get_permission(id)
        assert response["permission"]["id"] == id
        assert response["permission"]["custom"]
        assert not response["permission"]["owner"]
        assert response["permission"]["action"] == custom["action"]

        custom["owner"] = True
        await client.update_permission(id, custom)

        wait()
        response = await client.get_permission(id)
        assert response["permission"]["id"] == id
        assert response["permission"]["custom"]
        assert response["permission"]["owner"]
        assert response["permission"]["action"] == custom["action"]

        response = await client.list_permissions()
        original_len = len(response["permissions"])
        assert response["permissions"][0]["id"] == id
        await client.delete_permission(id)
        wait()
        response = await client.list_permissions()
        assert len(response["permissions"]) == original_len - 1

        await client.create_role(role)
        wait()
        response = await client.list_roles()
        assert role in response["roles"]
        await client.delete_role(role)
        wait()
        response = await client.list_roles()
        assert role not in response["roles"]
