from docx.oxml import OxmlElement
from docx.oxml.ns import qn

GREEK = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ε",
    "theta": "θ",
    "lambda": "λ",
    "mu": "μ",
    "nu": "ν",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "phi": "φ",
    "omega": "ω",
    "Delta": "Δ",
    "Sigma": "Σ",
    "Omega": "Ω",
    "Phi": "Φ",
    "Psi": "Ψ",
    "Gamma": "Γ",
    "Lambda": "Λ",
    "Pi": "Π",
}
SYMBOLS = {
    "times": "×",
    "div": "÷",
    "pm": "±",
    "mp": "∓",
    "cdot": "·",
    "leq": "≤",
    "geq": "≥",
    "neq": "≠",
    "ne": "≠",
    "approx": "≈",
    "infty": "∞",
    "rightarrow": "→",
    "leftarrow": "←",
    "Rightarrow": "⇒",
    "to": "→",
    "in": "∈",
    "sum": "∑",
    "prod": "∏",
    "int": "∫",
    "partial": "∂",
    "ell": "ℓ",
    "ldots": "…",
    "cdots": "⋯",
    "quad": " ",
    "qquad": " ",
    ",": " ",
    ";": " ",
    " ": " ",
}
SKIP_COMMANDS = {"left", "right", "mathrm", "mathbf", "mathit", "text", "operatorname", "displaystyle"}


def _m(tag: str) -> OxmlElement:
    return OxmlElement(f"m:{tag}")


def _mt(text: str) -> OxmlElement:
    run = _m("r")
    node = _m("t")
    node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = text
    run.append(node)
    return run


def _wrap_many(elements: list[OxmlElement]) -> OxmlElement:
    if len(elements) == 1:
        return elements[0]
    box = _m("e")
    for element in elements:
        box.append(element)
    return box


def tokenize(latex: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    text = latex.replace("\n", " ")
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "\\":
            index += 1
            if index >= len(text):
                break
            nxt = text[index]
            if nxt.isalpha():
                start = index
                while index < len(text) and text[index].isalpha():
                    index += 1
                tokens.append("\\" + text[start:index])
                continue
            tokens.append("\\" + nxt)
            index += 1
            continue
        tokens.append(char)
        index += 1
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def take(self) -> str | None:
        token = self.peek()
        if token is not None:
            self.pos += 1
        return token

    def parse_list(self, stop: set[str]) -> list[OxmlElement]:
        items: list[OxmlElement] = []
        while self.peek() is not None and self.peek() not in stop:
            items.append(self.parse_atom())
        return items or [_mt("")]

    def parse_group(self) -> list[OxmlElement]:
        if self.peek() == "{":
            self.take()
            items = self.parse_list({"}"})
            if self.peek() == "}":
                self.take()
            return items
        return [self.parse_atom()]

    def parse_nucleus(self) -> OxmlElement:
        token = self.take()
        if token is None:
            return _mt("")
        if token == "{":
            items = self.parse_list({"}"})
            if self.peek() == "}":
                self.take()
            return _wrap_many(items)
        if token == "\\frac":
            return self._fraction()
        if token == "\\sqrt":
            return self._sqrt()
        if token in {"\\sum", "\\prod", "\\int"}:
            return _mt(SYMBOLS[token[1:]])
        if token.startswith("\\"):
            name = token[1:]
            if name in SKIP_COMMANDS:
                if self.peek() == "{":
                    return _wrap_many(self.parse_group())
                return self.parse_nucleus()
            if name in GREEK:
                return _mt(GREEK[name])
            if name in SYMBOLS:
                return _mt(SYMBOLS[name])
            return _mt(name)
        if token.isdigit() or token == ".":
            chars = [token]
            while self.peek() is not None and (self.peek().isdigit() or self.peek() == "."):
                chars.append(self.take() or "")
            return _mt("".join(chars))
        return _mt(token)

    def parse_atom(self) -> OxmlElement:
        base = self.parse_nucleus()
        sub = sup = None
        while self.peek() in {"^", "_"}:
            op = self.take()
            script = self.parse_nucleus()
            if op == "^":
                sup = script
            else:
                sub = script
        if sub is not None and sup is not None:
            node = _m("sSubSup")
            node.append(_e(base))
            node.append(_named("sub", sub))
            node.append(_named("sup", sup))
            return node
        if sub is not None:
            node = _m("sSub")
            node.append(_e(base))
            node.append(_named("sub", sub))
            return node
        if sup is not None:
            node = _m("sSup")
            node.append(_e(base))
            node.append(_named("sup", sup))
            return node
        return base

    def _fraction(self) -> OxmlElement:
        node = _m("f")
        node.append(_fill("num", self.parse_group()))
        node.append(_fill("den", self.parse_group()))
        return node

    def _sqrt(self) -> OxmlElement:
        rad = _wrap_many(self.parse_group())
        node = _m("rad")
        props = _m("radPr")
        hide = _m("degHide")
        hide.set(qn("m:val"), "1")
        props.append(hide)
        node.append(props)
        node.append(_m("deg"))
        node.append(_e(rad))
        return node


def _e(child: OxmlElement) -> OxmlElement:
    if child.tag == qn("m:e"):
        return child
    return _named("e", child)


def _named(tag: str, child: OxmlElement) -> OxmlElement:
    node = _m(tag)
    node.append(child)
    return node


def _fill(tag: str, children: list[OxmlElement]) -> OxmlElement:
    node = _m(tag)
    for child in children:
        node.append(child)
    return node


def latex_to_omath(latex: str) -> OxmlElement:
    omath = _m("oMath")
    try:
        parser = _Parser(tokenize(latex))
        for item in parser.parse_list(set()):
            omath.append(item)
        if not len(omath):
            omath.append(_mt(latex))
    except Exception:
        omath.append(_mt(latex))
    return omath


def append_omath(paragraph, latex: str) -> None:
    paragraph._p.append(latex_to_omath(latex))
