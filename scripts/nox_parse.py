# Static (no-exec) parser for NoxInfluencer ranking page __NUXT__ payload.
# Parses the JS object literal as data; identifiers resolve to the IIFE's argument literals.
import re, sys, json


class P:
    def __init__(self, s, env):
        self.s = s; self.i = 0; self.env = env

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \n\r\t':
            self.i += 1

    def val(self):
        self.ws(); c = self.s[self.i]
        if c == '{':
            return self.obj()
        if c == '[':
            return self.arr()
        if c in '"\'':
            return self.string()
        m = re.compile(r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?').match(self.s, self.i)
        if m:
            self.i = m.end(); t = m.group(0)
            return float(t) if re.search(r'[.eE]', t) else int(t)
        m = re.compile(r'void 0|[A-Za-z_$][\w$]*').match(self.s, self.i)
        if m:
            self.i = m.end(); t = m.group(0)
            if t == 'true': return True
            if t == 'false': return False
            if t in ('null', 'void 0', 'undefined'): return None
            if t == 'Array':  # Array(n) -> skip
                self.ws()
                if self.s[self.i] == '(':
                    depth = 0
                    while True:
                        ch = self.s[self.i]; self.i += 1
                        if ch == '(': depth += 1
                        elif ch == ')':
                            depth -= 1
                            if depth == 0: break
                return []
            return self.env.get(t)
        raise ValueError('bad char %r at %d' % (c, self.i))

    def string(self):
        q = self.s[self.i]; j = self.i + 1; buf = []
        while self.s[j] != q:
            if self.s[j] == '\\':
                buf.append(self.s[j:j + 2]); j += 2
                if buf[-1] == '\\u':
                    buf[-1] += self.s[j:j + 4]; j += 4
            else:
                buf.append(self.s[j]); j += 1
        raw = ''.join(buf); self.i = j + 1
        try:
            return json.loads('"' + raw.replace('"', '\\"').replace('\\\\"', '\\"') + '"')
        except Exception:
            return raw

    def key(self):
        self.ws()
        if self.s[self.i] in '"\'':
            return self.string()
        m = re.compile(r'[\w$]+').match(self.s, self.i); self.i = m.end(); return m.group(0)

    def obj(self):
        self.i += 1; d = {}
        while True:
            self.ws()
            if self.s[self.i] == '}':
                self.i += 1; return d
            k = self.key(); self.ws(); assert self.s[self.i] == ':'; self.i += 1
            d[k] = self.val(); self.ws()
            if self.s[self.i] == ',': self.i += 1

    def arr(self):
        self.i += 1; a = []
        while True:
            self.ws()
            if self.s[self.i] == ']':
                self.i += 1; return a
            a.append(self.val()); self.ws()
            if self.s[self.i] == ',': self.i += 1


def parse(path):
    h = open(path, encoding='utf8').read()
    m = re.search(r'window\.__NUXT__=\(function\(([^)]*)\)\{(.*)\}\((.*?)\)\);?\s*</script>', h, re.S)
    if not m:
        return []
    names = m.group(1).split(','); body = m.group(2)
    argp = P('[' + m.group(3) + ']', {})
    args = argp.arr()
    env = dict(zip(names, args))
    k = body.find('rankDataList:[')
    if k < 0:
        return []
    p = P(body, env); p.i = k + len('rankDataList:')
    return p.arr()


if __name__ == '__main__':
    print(json.dumps(parse(sys.argv[1]), ensure_ascii=False))
