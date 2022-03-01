import socket
import threading
import sys


class Player(threading.Thread):
    """Thread to manage each Tic-Tac-Toe client individually"""

    def __init__(self, connection, server, number):
        """Initialize thread and setup variables"""

        threading.Thread.__init__(self)

        # specify player's mark
        if number == 0:
            self.mark = "X"
        else:
            self.mark = "O"

        self.connection = connection
        self.server = server
        self.number = number
        self.counter = 1

    def otherPlayerMoved(self, location):

        self.connection.send("15Opponent moved.".encode('ascii'))
        self.connection.send(str(location).encode('ascii'))

    def run(self):
        """Play the game"""

        # send client message indicating its mark (X or O)
        self.server.display("Player %s connected." % self.mark)
        self.connection.send(self.mark.encode('ascii'))

        # wait for another player to arrive
        if self.mark == "X":
            self.connection.send("29Waiting for another player...".encode('ascii'))
            self.server.gameBeginEvent.wait()
            self.connection.send(
                "34Other player connected. Your move.".encode('ascii'))
        else:
            self.server.gameBeginEvent.wait()  # wait for server
            self.connection.send("25Waiting for first move...".encode('ascii'))

        # play game until over
        while not self.server.gameOver():

            # get more location from client
            location = self.connection.recv(1).decode('ascii')

            if not location:
                break

            # check for valid move
            if self.server.validMove(int(location), self.number):
                self.server.display("loc: " + location)
                self.connection.send("11Valid move.".encode('ascii'))

            else:
                self.connection.send("24Invalid move, try again.".encode('ascii'))

        # close connection to client
        self.connection.close()
        self.server.display("Game over.")
        self.server.display("Connection closed.")


class TicTacToeServer:
    """Server that maintains a game of Tic-Tac-Toe for two clients"""

    def __init__(self):
        """Initialize variables and setup server"""

        HOST = "127.0.0.1"
        PORT = 5000

        self.board = []
        self.counter = 1
        self.currentPlayer = 0
        self.turnCondition = threading.Condition()
        self.gameBeginEvent = threading.Event()
        self.WIN_COMBINATIONS = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8),
                                 (2, 4, 6), ]

        for i in range(9):
            self.board.append(None)

        # setup server socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((HOST, PORT))
        self.display("Server awaiting connections...")

    def execute(self):
        """Play the game--create and start both Player threads"""

        self.players = []

        # wait for and accept two client connections
        for i in range(2):
            self.server.listen(2)
            connection, address = self.server.accept()

            # assign each client to a Player thread
            self.players.append(Player(connection, self, i))
            self.players[-1].start()

        self.server.close()  # no more connections to wait for

        # players are suspended until player O connects
        # resume players now
        self.gameBeginEvent.set()

    def display(self, message):
        """Display a message on the server"""

        print(message)

    def validMove(self, location, player):
        """Determine if a move is valid--if so, make move"""

        # only one move can be made at a time
        self.turnCondition.acquire()

        # while not current player, must wait for turn
        while player != self.currentPlayer:
            self.turnCondition.wait()

        # make move if location is not occupied
        if not self.isOccupied(location):

            # set move on board
            if self.currentPlayer == 0:
                self.board[location] = "X"
            else:
                self.board[location] = "O"

            # change current player
            self.currentPlayer = (self.currentPlayer + 1) % 2
            self.players[self.currentPlayer].otherPlayerMoved(
                location)

            # tell waiting player to continue
            self.turnCondition.notify()
            self.turnCondition.release()

            # valid move
            self.counter += 1
            self.check_gameOver()
            return 1

        # invalid move
        else:
            self.turnCondition.notify()
            self.turnCondition.release()
            return 0

    def isOccupied(self, location):
        """Determine if a space is occupied"""

        return self.board[location]  # an empty space is None

    def gameOver(self):
        return 0

    def check_gameOver(self):
        """Determine if the game is over"""
        if self.counter == 9:
            print("GAME OVER")
            return sys.exit(0)


def main():
    TicTacToeServer().execute()


if __name__ == "__main__":
    main()
