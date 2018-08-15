import $ from 'jquery';

const TRANSPILER_TARGET = 'http://35.233.200.194/compile'

class Compiler {

static Compile(lang, code, callback, error) {
    if (lang === 'java') this.Java(code, callback, error);
    else if (lang === 'javascript') this.JS(code, callback, error);
    else if (lang === 'python') this.Python(code, callback, error);
}

static Python(code, callback, error) {
let source = `
bc = {
    'NORTH':     2,
    'NORTHEAST': 1,
    'EAST':      0,
    'SOUTHEAST': 7,
    'SOUTH':     6,
    'SOUTHWEST': 5,
    'WEST':      4,
    'NORTHWEST': 3,
    'EMPTY':     0,
    'HOLE':     -1
}

class BCAbstractRobot:
    def __init__(self):
        self._bc_game_state = None
        self._bc_signal = None
        self._bc_clear_logs = False

        self._bc_logs = []

        # Robot id, never changes.
        self.id = null

    def _do_turn(self, game_state):
        self._bc_game_state = game_state
        if not self.id:
            this.id = self.me().id
        
        t = self.turn()
        if t is None:
            t = self._bc_null_action()
        
        self._bc_clear_logs = True
        return t

    def _bc_action(self, dir, action):
        return {
            'signal': self.signal,
            'logs': self._bc_logs,
            'dir': dir,
            'action': action
        }

    def _bc_null_action(self):
        return {
            'signal': self.signal,
            'logs': self._bc_logs
        }

    def signal(self, value):
        self.signal = value

    def get_robot(self, id):
        if id <= 0:
            return None
        for robot in self._bc_game_state.visible:
            if robot.id == id:
                return robot

    def get_visible_map(self):
        return self._bc_game_state.shadow

    def get_visible_robots(self):
        return self._bc_game_state.visible

    def me(self):
        return self.get_robot(self.get_visible_map()[3][3])

    def get_relative_pos(self, dx, dy):
        if dx < -3 or dx > 3 or dy < -3 or dy > 3:
            return None

        vis = self.get_visible_map()[dy][dx]
        if vis > 0:
            return self.get_robot(vis)
        else:
            return vis

    def log(self, message):
        if self._bc_clear_logs:
            self._bc_logs = []
            self._bc_clear_logs = False

        self._bc_logs.append(message)

    def move(self, direction):
        return self._bc_action(direction, 'move')

    def attack(self, direction):
        return self._bc_action(direction, 'attack')

    def turn(self):
        return None

${code}

robot = MyRobot()`

let message = {'lang':'python', 'src':source}

$.ajax({
    type: "POST",
    url: TRANSPILER_TARGET,
    data: JSON.stringify(message),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function(data){
        if (data['success']) {
            var d = data['js'].split("\n");
            d[d.length-4] = 'var robot = robot();'
            d[0] = "";
            d = d.join("\n");
            callback(d);
        } else error(data['error']);
    },
    failure: function(errMsg) {
        console.log("FAILURE: " + errMsg);
    }
});

}

static Java(code, callback, error) {

let game_state = `
package robot;
import java.util.ArrayList;

@jsweet.lang.Interface
public class GameState {
    public int[][] shadow;
    public ArrayList<Robot> visible;
}
`

let bc = `
package robot;

public class bc {
    public static final int NORTH = 2;
    public static final int NORTHEAST = 1;
    public static final int EAST = 0;
    public static final int SOUTHEAST = 7;
    public static final int SOUTH = 6;
    public static final int SOUTHWEST = 5;
    public static final int WEST = 4;
    public static final int NORTHWEST = 3;
    public static final int EMPTY = 0;
    public static final int HOLE = 1;
}
`

let robot = `
package robot;

@jsweet.lang.Interface
public class Robot {
    public int id;

    @jsweet.lang.Optional
    public int health;
    @jsweet.lang.Optional
    public int team;
    @jsweet.lang.Optional
    public int x;
    @jsweet.lang.Optional
    public int y;
}
`

let abstract_robot = `
package robot;
import java.util.ArrayList;

public class BCAbstractRobot {
    private GameState gameState;
    private int signal;
    private boolean clearLogs;
    private ArrayList<String> logs;
    private int id;

    public BCAbstractRobot() {
        logs = new ArrayList<String>();
    }

    public Action _do_turn(GameState _gameState) {
        gameState = _gameState;
        id = me().id;

        Action t = turn();
        clearLogs = true;

        return t;
    }

    public void signal(int value) {
        signal = value;
    }

    public Robot getRobot(int id) {
        if (id <= 0) return null;
        for (Robot r : gameState.visible) {
            if (r.id == id) {
                return r;
            }
        } return null;
    }

    public int[][] getVisibleMap() {
        return gameState.shadow;
    }

    public ArrayList<Robot> getVisibleRobots() {
        return gameState.visible;
    }

    public Robot me() {
        return getRobot(getVisibleMap()[3][3]);
    }

    public void log(String message) {
        if (clearLogs) {
            logs.clear();
            clearLogs = false;
        }
        
        logs.add(message);
    }

    public Action move(int direction) {
        return new Action("move",direction,signal,logs);
    }

    public Action attack(int direction) {
        return new Action("attack",direction,signal,logs);
    }
    
    public Action turn() {
        return null;
    }
}
`

let action = `
package robot;
import java.util.ArrayList;

public class Action {
    String action;
    int dir;
    int signal;
    ArrayList<String> logs;
    
    public Action(String type, int direction, int signal, ArrayList<String> logs) {
        this.dir = direction;
        this.action = type;
        this.signal = signal;
        this.logs = logs;
    }
}
`

let message = {'lang':'java', 'src':[
    {'filename':'BCAbstractRobot.java', 'source':abstract_robot},
    {'filename':'Action.java', 'source':action},
    {'filename':'MyRobot.java', 'source':code},
    {'filename':'GameState.java', 'source':game_state},
    {'filename':'Robot.java', 'source':robot},
    {'filename':'bc.java', 'source':bc}
]}

let postfix = "\nvar robot = {'robot':new robot.MyRobot()};";

$.ajax({
    type: "POST",
    url: TRANSPILER_TARGET,
    data: JSON.stringify(message),
    contentType: "application/json; charset=utf-8",
    dataType: "json",
    success: function(data){
        if (data['success']) callback(data['js']+postfix);
        else error(data['error']);
    },
    failure: function(errMsg) {
        console.log("FAILURE: " + errMsg);
    }
});


}

static JS(code, callback) {
let res =  `
let bc = {
    'NORTH':     2,
    'NORTHEAST': 1,
    'EAST':      0,
    'SOUTHEAST': 7,
    'SOUTH':     6,
    'SOUTHWEST': 5,
    'WEST':      4,
    'NORTHWEST': 3,
    'EMPTY':     0,
    'HOLE':     -1
}

class BCAbstractRobot {
    constructor() {
        // Internal robot state representation
        this._bc_game_state = null;
        this._bc_signal = null;

        this._bc_in_browser = (typeof _bc_browser_log !== 'undefined');
        this._bc_logs = [];
        this._bc_clear_logs = false;

        // Robot id, never changes.
        this.id = null;
    }

    // Hook called by runtime, sets state and calls turn.
    _do_turn(game_state) {
        this._bc_game_state = game_state;
        if (!this.id) this.id = this.me().id;
        var t = this.turn();
        if (t === null) t = this._bc_null_action();

        this._bc_clear_logs = true;
        return t;
    }

    // Action template
    _bc_action(dir, action) {
        return {
            'signal': this.signal,
            'logs': this._bc_logs,
            'dir': dir,
            'action': action
        };
    }

    // Action template
    _bc_null_action() {
        return {
            'signal': this.signal,
            'logs': this._bc_logs
        };
    }
    
    // Set signal value.
    signal(value) {
        this.signal = value;
    }

    // Get robot of a given ID
    getRobot(id) {
        if (id <= 0) return null;
        for (var i=0; i<this._bc_game_state.visible.length; i++) {
            if (this._bc_game_state.visible[i].id === id) {
                return this._bc_game_state.visible[i];
            }
        } return null;
    }

    // Get current robot vision.
    getVisibleMap() {
        return this._bc_game_state.shadow;
    }

    // Get a list of robots visible to you.
    getVisibleRobots() {
        return this._bc_game_state.visible;
    }

    // Get me.
    me() {
        return this.getRobot(this.getVisibleMap()[3][3]);
    }

    // Get the square dx, dy away.
    getRelativePos(dX, dY) {
        if (dX < -3 || dX > 3 || dY < -3 || dY > 3) return null;
        var vis = this.getVisibleMap()[dY][dX];

        if (vis > 0) return this.getRobot(vis);
        else return vis;
    }

    // If in browser, direct print, otherwise put in message.
    log(message) {
        if (this._bc_clear_logs) {
            this._bc_logs = [];
            this._bc_clear_logs = false;
        }

        if (this._bc_in_browser) _bc_browser_log(this.id, message);
        else this._bc_logs.push(message);
    }

    // Move in a direction
    move(direction) {
        return this._bc_action(direction, 'move');
    }

    // Attack in a direction
    attack(direction) {
        return this._bc_action(direction, 'attack');
    }

    turn() {
        return null;
    }
}


${code}

var robot = {'robot':new MyRobot()};
`

callback(res);

}

}

export default Compiler;