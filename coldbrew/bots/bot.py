__pragma__('iconv')
__pragma__('tconv')
#__pragma__('opov')

class BCAbstractRobot:
    def __init__(self):
        self._bc_reset_state()

    def _do_turn(self, game_state):
        self._bc_game_state = game_state
        self.id = game_state['id']
        self.karbonite = game_state['karbonite']
        self.fuel = game_state['fuel']
        self.last_offer = game_state['last_offer']

        self.me = self.get_robot(self.id)

        try:
            t = self.turn()
        except Exception as e:
            t = self._bc_error_action(e)

        if not t:
            t = self._bc_null_action()

        self._bc_reset_state()

        return t

    def _bc_reset_state(self):
        # Internal robot state representation
        self._bc_logs = [];
        self._bc_signal = 0;
        self._bc_signal_radius = 0;
        self._bc_game_state = None;
        self._bc_castle_talk = 0;
        
        self.me = None;
        self.id = None;
        self.fuel = None;
        self.karbonite = None;
        self.last_offer = None;

    def _bc_null_action(self):
        return {
            'signal': self._bc_signal,
            'signal_radius': self._bc_signal_radius,
            'logs': self._bc_logs,
            'castle_talk': self._bc_castle_talk
        }

    def _bc_error_action(self, e):
        a = self._bc_null_action()
        a['error'] = str(e)

        return a

    def _bc_action(self, action, properties=None):
        a = self._bc_null_action()
        
        if properties:
            for key in properties:
                a[key] = properties[key]

        a['action'] = action

        return a


    def _bc_check_on_map(self, x, y):
        return x >= 0 and x < len(self._bc_game_state['shadow'][0]) and y >= 0 and y < len(self._bc_game_state['shadow'])


    def log(self, message):
        self._bc_logs.append(str(message))


    def signal(self, value, radius):
        # Check if enough fuel to signal, and that valid value.
        if self.fuel < radius:
            raise Exception("Not enough fuel to signal given radius.")
        
        if value < 0 or value >= 2**SPECS['COMMUNICATION_BITS']:
            raise Exception("Invalid signal, must be int within bit range.")
        
        if radius > 2*((SPECS['MAX_BOARD_SIZE']-1)**2):
            raise Exception("Signal radius is too big.")

        self._bc_signal = value
        self._bc_signal_radius = radius

        self.fuel -= radius

    def castle_talk(self, value):
        if value < 0 or value >= SPECS['CASTLE_TALK_BITS']**2:
            raise Exception('Invalid castle talk, must be between 0 and 2^8.')

        self._bc_castle_talk = value

    def propose_trade(self, karbonite, fuel):
        if self.me['unit'] != SPECS['CASTLE']:
            raise Exception("Only castles can trade.")
        
        if abs(karbonite) >= SPECS['MAX_TRADE'] or abs(fuel) >= SPECS['MAX_TRADE']:
            raise Exception("Cannot trade over " + str(SPECS['MAX_TRADE']) + " in a given turn.")

        return self._bc_action('trade', {
            'trade_fuel': fuel,
            'trade_karbonite': karbonite
        })
    

    def build_unit(self, unit, dx, dy):
        if self.me['unit'] != SPECS['PILGRIM'] and self.me['unit'] != SPECS['CASTLE'] and self.me['unit'] != SPECS['CHURCH']:
            raise Exception("This unit type cannot build.")
        if self.me['unit'] == SPECS['PILGRIM'] and unit != SPECS['CHURCH']:
            raise Exception("Pilgrims can only build churches.")
        if self.me['unit'] != SPECS['PILGRIM'] and unit == SPECS['CHURCH']:
            raise Exception("Only pilgrims can build churches.")
        
        if dx < -1 or dy < -1 or dx > 1 or dy > 1:
            raise Exception("Can only build in adjacent squares.")
        if not self._bc_check_on_map(self.me['x']+dx,self.me['y']+dy):
            raise Exception("Can't build units off of map.")
        if self._bc_game_state['shadow'][self.me['y']+dy][self.me['x']+dx] != 0:
            raise Exception("Cannot build on occupied tile.")
        if not self._bc_game_state['map'][self.me['y']+dy][self.me['x']+dx]:
            raise Exception("Cannot build onto impassable terrain.")
        if self.karbonite < SPECS['UNITS'][unit]['CONSTRUCTION_KARBONITE'] or self.fuel < SPECS['UNITS'][unit]['CONSTRUCTION_FUEL']:
            raise Exception("Cannot afford to build specified unit.")

        return self._bc_action('build', {
            'dx': dx, 'dy': dy,
            'build_unit': unit
        })
    

    def move(self, dx, dy):
        if self.me['unit'] == SPECS['CASTLE'] or self.me['unit'] == SPECS['CHURCH']:
            raise Exception("Churches and Castles cannot move.")
        if not self._bc_check_on_map(self.me['x']+dx,self.me['y']+dy):
            raise Exception("Can't move off of map.")
        if self._bc_game_state.shadow[self.me['y']+dy][self.me['x']+dx] is None:
            raise Exception("Cannot move outside of vision range.")
        if self._bc_game_state.shadow[self.me['y']+dy][self.me['x']+dx] != 0:
            raise Exception("Cannot move onto occupied tile.")
        if not self._bc_game_state.map[self.me['y']+dy][self.me['x']+dx]:
            raise Exception("Cannot move onto impassable terrain.")

        r = dx**2 + dy**2  # Squared radius
        if r > SPECS['UNITS'][self.me['unit']]['SPEED']:
            raise Exception("Slow down, cowboy.  Tried to move faster than unit can.")
        if self.fuel < r*SPECS['UNITS'][self.me['unit']]['FUEL_PER_MOVE']:
            raise Exception("Not enough fuel to move at given speed.")

        return self._bc_action('move', {
            'dx': dx, 'dy': dy
        })
    
    def mine(self):
        if self.me['unit'] != SPECS['PILGRIM']:
            raise Exception("Only Pilgrims can mine.")
        if self.fuel < SPECS['MINE_FUEL_COST']:
            raise Exception("Not enough fuel to mine.")
        
        if self._bc_game_state['karbonite_map'][self.me['y']][self.me['x']]:
            if self.me['karbonite'] >= SPECS['UNITS'][SPECS['PILGRIM']]['KARBONITE_CAPACITY']:
                raise Exception("Cannot mine, as at karbonite capacity.")
        elif self._bc_game_state['fuel_map'][self.me['y']][self.me['x']]:
            if self.me['fuel'] >= SPECS['UNITS'][SPECS['PILGRIM']]['FUEL_CAPACITY']:
                raise Exception("Cannot mine, as at fuel capacity.")
        else:
            raise Exception("Cannot mine square without fuel or karbonite.")

        return self._bc_action('mine')
    

    def give(self, dx, dy, karbonite, fuel):
        if dx > 1 or dx < -1 or dy > 1 or dy < -1 or (dx == 0 and dy == 0):
            raise Exception("Can only give to adjacent squares.")
        if not self._bc_check_on_map(self.me['x']+dx,self.me['y']+dy):
            raise Exception("Can't give off of map.")
        if self._bc_game_state['shadow'][self.me['y']+dy][self.me['x']+dy] == 0:
            raise Exception("Cannot give to empty square.")
        if karbonite < 0 or fuel < 0 or self.me['karbonite'] < karbonite or self.me['fuel'] < fuel:
            raise Exception("Do not have specified amount to give.")

        return self._bc_action('give', {
            'dx':dx, 'dy':dy,
            'give_karbonite':karbonite,
            'give_fuel':fuel
        })
    

    def attack(self, dx, dy):
        if self.me['unit'] != SPECS['CRUSADER'] and self.me['unit'] != SPECS['PREACHER'] and self.me['unit'] != SPECS['PROPHET']:
            raise Exception("Given unit cannot attack.")
        
        if self.fuel < SPECS['UNITS'][self.me['unit']]['ATTACK_FUEL_COST']:
            raise Exception("Not enough fuel to attack.")
        if not self._bc_check_on_map(self.me['x']+dx,self.me['y']+dy):
            raise Exception("Can't attack off of map.")
        if self._bc_game_state['shadow'][self.me['y']+dy][self.me['x']+dx] is None:
            raise Exception("Cannot attack outside of vision range.")
        if not self._bc_game_state['map'][self.me['y']+dy][self.me['x']+dx]:
            raise Exception("Cannot attack impassable terrain.")
        if self._bc_game_state['shadow'][self.me['y']+dy][self.me['x']+dx] == 0:
            raise Exception("Cannot attack empty tile.")

        r = dx**2 + dy**2
        if r > SPECS['UNITS'][self.me['unit']]['ATTACK_RADIUS'][1] or r < SPECS['UNITS'][self.me['unit']]['ATTACK_RADIUS'][0]:
            raise Exception("Cannot attack outside of attack range.")

        return self._bc_action('attack', {
            'dx':dx, 'dy':dy
        })
        
    def get_robot(self, id):
        if id <= 0:
            return None

        for robot in self._bc_game_state['visible']:
            if robot['id'] == id:
                return robot
            
        return None

    def get_visible_robot_map():
        return self._bc_game_state['shadow']

    def get_passable_map():
        return self._bc_game_state['map']

    def get_karbonite_map():
        return self._bc_game_state['karbonite_map']

    def get_fuel_map():
        return self._bc_game_state['fuel_map']

    def get_visible_robots():
        return self._bc_game_state['visible']

    def turn(self):
        return None

class MyRobot(BCAbstractRobot):
    def __init__(self):
        self.step = -1
        super().__init__()

    def turn(self):
        self.step += 1

        if self.me['unit'] == SPECS['CRUSADER'] and self.me['team'] == SPECS['RED']:
            self.log("Crusader health: " + str(self.me['health']))
            return self.attack(-1,-1)

        elif self.me['unit'] == SPECS['CASTLE']:
            if self.step == 0:
                self.log("Building a crusader at " + str(self.me['x']+1) + ", " + str(self.me['y']+1))
                return self.build_unit(SPECS['CRUSADER'], 1, 1)

            else:
                self.log("Castle health: " + str(self.me['health']))
