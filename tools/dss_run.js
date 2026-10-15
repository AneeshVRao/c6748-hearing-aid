// Load a program on the LCDK, run it, halt, print variables. Debug Server Scripting (CCS 7).
// Usage: dss.bat tools/dss_run.js <target.ccxml> <program.out> <run_seconds> <expr> [<expr> ...]
//   run_seconds = 0: load only. REG:<name> reads a CPU register (e.g. REG:TSCL).
//   SET:<expr>:<value> writes; @N runs N more seconds before the next items.
// Example: dss.bat tools/dss_run.js LCDK_C6748.ccxml ccs/build/live/live.out 5 g_prof.isr_max g_ifft_gain
importPackage(Packages.com.ti.debug.engine.scripting);
importPackage(Packages.com.ti.ccstudio.scripting.environment);
importPackage(Packages.java.lang);

var a = arguments;
if (a.length < 3) { print("usage: dss_run.js ccxml out seconds [expr...]"); java.lang.System.exit(2); }
var env = ScriptingEnvironment.instance();
var server = env.getServer("DebugServer.1");
server.setConfig(a[0]);
var s = server.openSession(".*C674.*");
var code = 0;
try {
    s.target.connect();
    s.target.reset();
    s.memory.loadProgram(a[1]);
    var sec = parseFloat(a[2]);
    if (sec > 0) {
        s.target.runAsynch();
        print("RUNNING");
        Thread.sleep(Math.round(sec * 1000));
        s.target.halt();
    }
    for (var i = 3; i < a.length; i++) {
        if (a[i].charAt(0) == "@") {                 // @N: run N more seconds, then halt
            s.target.runAsynch(); Thread.sleep(Math.round(parseFloat(a[i].substring(1)) * 1000)); s.target.halt();
            print("-- ran " + a[i].substring(1) + " s more"); continue;
        }
        if (a[i].indexOf("SET:") == 0) {             // SET:<expr>:<value> (dss.bat cannot pass "=")
            var j = a[i].lastIndexOf(":"); s.expression.evaluate(a[i].substring(4, j) + " = " + a[i].substring(j + 1));
            print("-- " + a[i]); continue;
        }
        try { print(a[i] + " = " + (a[i].indexOf("REG:") == 0 ? s.memory.readRegister(a[i].substring(4)) : s.expression.evaluate(a[i]))); }
        catch (e) { print(a[i] + " = ERROR " + e); code = 1; }
    }
} catch (e) { print("DSS ERROR: " + e); code = 1; }
s.target.disconnect();
s.terminate();
server.stop();
java.lang.System.exit(code);
