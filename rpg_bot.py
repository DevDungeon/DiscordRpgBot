import pymysql.cursors
from settings import BOT_TOKEN, DB_HOST, DB_USER, DB_PASS, DB_NAME
from discord import Game
from discord.ext.commands import Bot

BOT_PREFIX = ("?", "!", "$", ".")


def connect_database():
    connection = pymysql.connect(host=DB_HOST,
                                 user=DB_USER,
                                 password=DB_PASS,
                                 db=DB_NAME,
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    print('[*] Connected to database: %s' % DB_NAME)
    return connection


class RpgBot:

    def __init__(self, token):
        self.db = connect_database()
        self.bot = Bot(command_prefix=BOT_PREFIX)
        self.token = token
        self.prepare_client()

    def run(self):
        self.bot.run(self.token)

    def prepare_client(self):
        @self.bot.event
        async def on_ready():
            await self.bot.change_presence(game=Game(name=" Dungeon Master"))
            self.add_all_users_to_db()
            print("[*] Connected to Discord as: " + self.bot.user.name)

        # on player join -> log player in db
        # say hello, convince them to play
        @self.bot.event
        async def on_member_join(member):
            self.add_user_to_db(member)

        # on message -> give player xp points (but only once per minute)
        # (in the add-xp function, check if they level up)
        @self.bot.event
        async def on_message(message):
            self.update_experience_points(message.author, 1)

        # TODO on level up -> add item to inventory

        # !stats - check your xp and attributes
        # !rank - list top X players on the server
        # !inventory - list your inventory

        @self.bot.command(name='stats',
                          description="Get detailed information about your RPG character.",
                          brief="RPG player stats",
                          aliases=['statistics'],
                          pass_context=True)
        async def stats(context):
            player = self.get_player(context.message.author)
            await self.bot.say("So you want stats?")
            await self.bot.say("""`
Stats for %s

Joined server: %s
Experience points: %s`""" % (context.message.author.mention, player['join_server_date'], player['xp_points']))

            # TODO what can you with xp points? get commands? attack people? craft stuff?

    def get_player(self, user_id):
        try:
            with self.db.cursor() as cursor:
                sql = "SELECT `user_id`, `join_server_date`, `xp_points` FROM `players` WHERE `user_id`=%s"
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                if not result:
                    print("User does not exist: %s" % user_id)
                else:
                    return result
        except Exception as e:
            print("Error looking up userid %s.\n%s" % (user_id, e))

    def add_all_users_to_db(self):
        for member in self.bot.get_all_members():
            self.add_user_to_db(member)

    def add_user_to_db(self, member):
        if self.get_player(member.id):
            return

        try:
            with self.db.cursor() as cursor:
                sql = "INSERT INTO `players` (`user_id`, `join_server_date`, `xp_points`)" + \
                      " VALUES (%s, %s, %s)"
                cursor.execute(sql, (member.id, member.joined_at, 0))
            self.db.commit()
            print("Added user %s to database." % member.id)
        except Exception as e:
            print("Error adding user: %s" % e)

    def update_experience_points(self, member, points):
        player_info = self.get_player(member.id)
        with self.db.cursor() as cursor:
            try:
                sql = "UPDATE players SET xp_points=%s WHERE user_id=%s"
                new_point_value = player_info['xp_points'] + points
                cursor.execute(sql, (new_point_value, member.id))
                self.db.commit()
                print("[*] Updated user %s experience points from %s to %s." %
                      (member.name, player_info['xp_points'], new_point_value))
            except Exception as e:
                print("[-] Error updating xp points for %s; %s" % (member.id, e))


if __name__ == '__main__':
    bot = RpgBot(BOT_TOKEN)
    bot.run()
