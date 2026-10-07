import { lstat, realpath, stat } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";

const root = resolve(import.meta.dir, "..");
const skill = "skills/launching-free-tier-startups/SKILL.md";
const hero = "assets/readme/hero.svg";
const playbook = "skills/launching-free-tier-startups/references/service-playbook.md";
const artwork = [
  hero,
  "assets/readme/hero.source.svg",
  "assets/readme/services/cloudflare.svg",
  "assets/readme/services/convex.svg",
  "assets/readme/services/better-auth.svg",
  "assets/readme/services/posthog.svg",
  "assets/readme/services/cloudflare-r2.svg",
];

function assert(value: unknown, message: string): asserts value {
  if (!value) throw new Error(message);
}

function inside(path: string) {
  const offset = relative(root, path);
  assert(offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset), "path escapes repository");
}

function entities(value: string) {
  const named: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
  const decoded = value.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos);/gi, (_, entity: string) =>
    entity.startsWith("#")
      ? String.fromCodePoint(Number.parseInt(entity.slice(/^#x/i.test(entity) ? 2 : 1), /^#x/i.test(entity) ? 16 : 10))
      : named[entity.toLowerCase()] ?? "",
  );
  assert(!/&(?:#|[a-z]+;)/i.test(decoded), "unsupported character entity");
  return decoded;
}

async function link(document: string, raw: string) {
  try {
    const target = entities(raw.replace(/^<|>$/g, ""));
    assert(target.length > 0 && !/[\\\u0000-\u0020\u007f]/.test(target), "invalid link target");
    if (/^https:\/\//i.test(target)) {
      assert(new URL(target).protocol === "https:", "external links must use HTTPS");
      return;
    }
    if (target.startsWith("#")) return;
    assert(!/^(?:[a-z][\w+.-]*:|\/)/i.test(target), "use HTTPS, a relative file path, or a local anchor");
    const path = target.split(/[?#]/, 1)[0];
    assert(path, "missing local file path");
    const destination = resolve(dirname(resolve(root, document)), decodeURIComponent(path));
    inside(destination);
    const actual = await realpath(destination);
    inside(actual);
    assert((await stat(actual)).isFile(), "local link must target a regular file");
  } catch (error) {
    throw new Error(`${document}: ${raw}: ${error instanceof Error ? error.message : error}`);
  }
}

try {
  for (const file of ["README.md", "LICENSE", skill, "skills/launching-free-tier-startups/LICENSE", playbook, "scripts/outline_hero.py", ...artwork]) {
    const path = resolve(root, file);
    assert((await lstat(path)).isFile(), `${file}: required regular file missing`);
    inside(await realpath(path));
  }

  const skillText = await Bun.file(resolve(root, skill)).text();
  const header = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(skillText);
  assert(header, `${skill}: missing YAML frontmatter`);
  const metadata = Bun.YAML.parse(header[1]);
  assert(metadata && typeof metadata === "object" && !Array.isArray(metadata), `${skill}: frontmatter must be a mapping`);
  assert("name" in metadata && metadata.name === "launching-free-tier-startups", `${skill}: incorrect skill name`);
  assert("description" in metadata && typeof metadata.description === "string" && metadata.description.trim().length >= 20 && metadata.description.length <= 1024 && /[a-z]{3}/i.test(metadata.description), `${skill}: description must be meaningful text (20–1024 characters)`);

  // ponytail: inline Markdown and quoted HTML only; add a parser if the docs adopt richer link syntax.
  for (const document of ["README.md", skill, playbook]) {
    const text = (await Bun.file(resolve(root, document)).text())
      .replace(/^(`{3,}|~{3,})[^\n]*\n[\s\S]*?^\1[ \t]*$/gm, "")
      .replace(/`[^`\n]*`/g, "")
      .replace(/<!--[\s\S]*?-->/g, "");
    for (const match of text.matchAll(/\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+["'][^"'\n]*["'])?\s*\)/g)) {
      await link(document, match[1]);
    }
    for (const match of text.matchAll(/\b(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)')/gi)) {
      await link(document, match[1] ?? match[2]);
    }
    for (const match of text.matchAll(/<([a-z][\w+.-]*:[^<>\s]+)>/gi)) {
      await link(document, match[1]);
    }
  }

  const elements: Record<string, true> = { svg: true, title: true, desc: true, g: true, rect: true, path: true, text: true, tspan: true, line: true, polyline: true, polygon: true, circle: true, ellipse: true, defs: true, clipPath: true, linearGradient: true, radialGradient: true, stop: true, mask: true, pattern: true, use: true };
  for (const file of artwork) {
    const svg = (await Bun.file(resolve(root, file)).text()).replace(/<!--[\s\S]*?-->/g, "");
    assert(/^\s*<svg\b/.test(svg), `${file}: expected SVG root`);
    assert(!/<!|<\?/.test(svg), `${file}: declarations and processing instructions are forbidden`);
    for (const tag of svg.matchAll(/<\/?([a-z][\w:.-]*)\b((?:[^"'<>]|"[^"]*"|'[^']*')*)>/gi)) {
      assert(Object.hasOwn(elements, tag[1]), `${file}: unsafe or unsupported element <${tag[1]}>`);
      for (const attribute of tag[2].matchAll(/([^\s=/'"]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g)) {
        const name = attribute[1].toLowerCase();
        const localName = name.split(":").pop() ?? "";
        const value = entities(attribute[2] ?? attribute[3]);
        assert(!localName.startsWith("on") && name !== "style" && name !== "xml:base" && localName !== "src", `${file}: unsafe attribute ${name}`);
        assert(!value.includes("\\"), `${file}: escaped attribute values are forbidden`);
        if (localName === "href") assert(/^#[\w:.-]+$/.test(value), `${file}: resource references must be local fragments`);
        const withoutLocalURLs = value.replace(/url\s*\(\s*(['"]?)#[\w:.-]+\1\s*\)/gi, "");
        assert(!/url\s*\(/i.test(withoutLocalURLs), `${file}: external or unsupported resource reference`);
      }
    }
  }
  console.log("check: skill metadata, repository files, document links, and SVG safety passed");
} catch (error) {
  console.error(`check: ${error instanceof Error ? error.message : error}`);
  process.exit(1);
}
