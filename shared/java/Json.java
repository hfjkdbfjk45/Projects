import java.util.*;

/** Small dependency-free JSON codec for CLI messages, not a replacement for Jackson in a large service. */
public final class Json {
    private final String input;
    private int pos;
    private Json(String input) { this.input = input; }
    public static Object parse(String input) {
        Json p = new Json(input);
        Object result = p.value(0); p.space();
        if (p.pos != input.length()) throw new IllegalArgumentException("Trailing JSON content");
        return result;
    }
    private void space() { while (pos < input.length() && Character.isWhitespace(input.charAt(pos))) pos++; }
    private char next() { if (pos == input.length()) throw new IllegalArgumentException("Truncated JSON"); return input.charAt(pos++); }
    private Object value(int depth) {
        if (depth > 32) throw new IllegalArgumentException("JSON nesting limit exceeded");
        space(); char c = next();
        if (c == '"') return string();
        if (c == '{') {
            Map<String,Object> m = new LinkedHashMap<>(); space();
            if (pos < input.length() && input.charAt(pos) == '}') { pos++; return m; }
            while (true) {
                space(); if (next() != '"') throw new IllegalArgumentException("Expected object key");
                String k = string(); space(); if (next() != ':') throw new IllegalArgumentException("Expected colon");
                if (m.containsKey(k)) throw new IllegalArgumentException("Duplicate JSON key: " + k);
                m.put(k, value(depth + 1)); space(); c = next();
                if (c == '}') return m;
                if (c != ',') throw new IllegalArgumentException("Expected comma");
            }
        }
        if (c == '[') {
            List<Object> a = new ArrayList<>(); space();
            if (pos < input.length() && input.charAt(pos) == ']') { pos++; return a; }
            while (true) {
                a.add(value(depth + 1)); space(); c = next();
                if (c == ']') return a;
                if (c != ',') throw new IllegalArgumentException("Expected comma");
            }
        }
        pos--;
        for (String lit : List.of("true", "false", "null")) {
            if (input.startsWith(lit, pos)) { pos += lit.length(); return lit.equals("null") ? null : lit.equals("true"); }
        }
        int start = pos;
        while (pos < input.length() && "-+0123456789.eE".indexOf(input.charAt(pos)) >= 0) pos++;
        String s = input.substring(start, pos);
        if (!s.matches("-?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?")) throw new IllegalArgumentException("Invalid JSON value");
        try { if (s.indexOf('.') < 0 && s.indexOf('e') < 0 && s.indexOf('E') < 0) return Long.parseLong(s); return new java.math.BigDecimal(s); }
        catch (NumberFormatException e) { throw new IllegalArgumentException("JSON number out of range"); }
    }
    private String string() {
        StringBuilder b = new StringBuilder();
        while (true) {
            char c = next(); if (c == '"') return b.toString();
            if (c < 32) throw new IllegalArgumentException("Unescaped control character");
            if (c == '\\') {
                c = next();
                switch(c) {
                    case '"', '\\', '/' -> b.append(c);
                    case 'b' -> b.append('\b'); case 'f' -> b.append('\f');
                    case 'n' -> b.append('\n'); case 'r' -> b.append('\r'); case 't' -> b.append('\t');
                    case 'u' -> { if (pos + 4 > input.length()) throw new IllegalArgumentException("Invalid Unicode escape"); b.append((char)Integer.parseInt(input.substring(pos, pos+4),16)); pos += 4; }
                    default -> throw new IllegalArgumentException("Invalid escape");
                }
            } else b.append(c);
        }
    }
    public static String write(Object v) {
        if (v == null) return "null";
        if (v instanceof String s) {
            StringBuilder b = new StringBuilder("\"");
            for (char c : s.toCharArray()) switch(c) {
                case '"' -> b.append("\\\""); case '\\' -> b.append("\\\\");
                case '\n' -> b.append("\\n"); case '\r' -> b.append("\\r"); case '\t' -> b.append("\\t");
                default -> { if (c < 32) b.append(String.format("\\u%04x",(int)c)); else b.append(c); }
            }
            return b.append('"').toString();
        }
        if (v instanceof Boolean) return v.toString();
        if (v instanceof Number n) {
            if (!Double.isFinite(n.doubleValue())) throw new IllegalArgumentException("Non-finite JSON number");
            return n.toString();
        }
        if (v instanceof Map<?,?> m) {
            StringJoiner j = new StringJoiner(",", "{", "}"); m.forEach((k,x) -> j.add(write(k.toString()) + ":" + write(x))); return j.toString();
        }
        if (v instanceof Iterable<?> a) { StringJoiner j = new StringJoiner(",", "[", "]"); for (Object x : a) j.add(write(x)); return j.toString(); }
        throw new IllegalArgumentException("Unsupported JSON value: " + v.getClass());
    }
    @SuppressWarnings("unchecked") public static Map<String,Object> object(Object v) {
        if (!(v instanceof Map)) throw new IllegalArgumentException("Expected JSON object"); return (Map<String,Object>)v;
    }
    @SuppressWarnings("unchecked") public static List<Object> array(Object v) {
        if (!(v instanceof List)) throw new IllegalArgumentException("Expected JSON array"); return (List<Object>)v;
    }
    public static String text(Map<String,Object> m, String k) {
        if (!(m.get(k) instanceof String s) || s.isBlank() || s.length() > 100) throw new IllegalArgumentException("Invalid " + k); return s;
    }
    public static long integer(Map<String,Object> m, String k, long min, long max) {
        if (!(m.get(k) instanceof Number n)) throw new IllegalArgumentException("Missing numeric " + k);
        long x;
        try { x = new java.math.BigDecimal(n.toString()).longValueExact(); } catch (ArithmeticException e) { throw new IllegalArgumentException("Expected integer " + k); }
        if (x < min || x > max) throw new IllegalArgumentException(k + " out of range"); return x;
    }
}
