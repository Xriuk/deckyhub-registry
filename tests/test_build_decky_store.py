import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from build_decky_store import build  # noqa: E402

HASH = "a" * 64


def entry(repo="Owner/Plug", name="Plug", **extra):
    return {"id": "plug", "name": name, "repo": repo, "category": "Utilities", "description": "Does things.", "asset": {"include": [".zip"], "exclude": ["source"]}, **extra}


def release(tag, day, digest=f"sha256:{HASH}", prerelease=False, **extra):
    return {"tag_name": tag, "published_at": f"2026-01-{day:02}T00:00:00Z", "prerelease": prerelease, "draft": False,
            "assets": [{"name": "plug.zip", "browser_download_url": f"https://x/{tag}.zip", "size": 3, "digest": digest}], **extra}


def no_manifest(asset):
    return {}


class BuildDeckyStoreTests(unittest.TestCase):
    def test_a_plugin_becomes_the_stores_shape_with_newest_version_first_and_the_zip_as_its_artifact(self):
        releases = {"owner/plug": [release("v1.0.0", 1), release("v1.1.0", 5, pluginVersion="1.1.0")]}
        plugins, updates = build([entry()], releases, lambda asset: {"name": "Real Name", "author": "Someone", "version": "1.1.0", "publish": {"tags": ["a", "b"], "image": "https://i/p.png"}})
        self.assertEqual(len(plugins), 1)
        plugin = plugins[0]
        self.assertEqual((plugin["id"], plugin["name"], plugin["author"], plugin["tags"], plugin["image_url"]), (1, "Real Name", "Someone", ["a", "b"], "https://i/p.png"))
        self.assertEqual([version["name"] for version in plugin["versions"]], ["1.1.0", "1.0.0"])
        self.assertEqual(plugin["versions"][0], {"name": "1.1.0", "hash": HASH, "artifact": "https://x/v1.1.0.zip", "created": "2026-01-05T00:00:00Z"})
        self.assertEqual(updates, {"Real Name": ["1.1.0", HASH, "https://x/v1.1.0.zip"]})

    def test_without_a_manifest_the_registrys_own_name_owner_and_category_are_used(self):
        plugins, _ = build([entry()], {"owner/plug": [release("v2.0.0", 1)]}, no_manifest)
        self.assertEqual((plugins[0]["name"], plugins[0]["author"], plugins[0]["tags"]), ("Plug", "Owner", ["utilities"]))
        self.assertTrue(plugins[0]["description"].startswith("Does things."))

    def test_prereleases_and_zips_without_a_published_sha256_are_left_out(self):
        releases = {"owner/plug": [release("v1.0.0", 1), release("v2.0.0-rc.1", 9, prerelease=True), release("v1.5.0", 5, digest=None)]}
        plugins, _ = build([entry()], releases, no_manifest)
        self.assertEqual([version["name"] for version in plugins[0]["versions"]], ["1.0.0"])

    def test_a_plugin_with_nothing_installable_is_not_listed(self):
        for releases in ([], [release("v1.0.0", 1, digest=None)], [release("v1.0.0-rc.1", 1, prerelease=True)], [release("latest", 1)]):
            self.assertEqual(build([entry()], {"owner/plug": releases}, no_manifest), ([], {}), releases)

    def test_two_plugins_with_one_name_leave_only_the_first(self):
        entries = [entry(repo="a/one", name="Same"), entry(repo="b/two", name="Same")]
        releases = {"a/one": [release("v1.0.0", 1)], "b/two": [release("v1.0.0", 1)]}
        plugins, updates = build(entries, releases, no_manifest)
        self.assertEqual([plugin["id"] for plugin in plugins], [1])
        self.assertEqual(list(updates), ["Same"])

    def test_the_description_and_tags_carry_deckyhub_warnings_and_a_link_when_stats_are_given(self):
        releases = {"owner/plug": [release("v1.0.0", 1)]}
        stats = {"owner/plug": {"root": True, "warnings": ["obfuscated", "persistence"], "ai": ["AGENTS.md"]}}
        plugin = build([entry()], releases, lambda asset: {"publish": {"tags": ["root", "x"]}}, stats)[0][0]
        self.assertEqual(plugin["tags"], ["root", "x", "ai-assisted", "deckyhub-warning"])
        self.assertTrue(plugin["description"].startswith("Does things.\n\nDeckyHub: warnings: obfuscated, persistence. Details: https://deckyhub.com/plugins/plug.html"))
        clean = build([entry()], releases, no_manifest, {"owner/plug": {"root": False}})[0][0]
        self.assertEqual((clean["tags"], clean["description"].endswith("DeckyHub: no audit warnings. Details: https://deckyhub.com/plugins/plug.html")), (["utilities"], True))
        without = build([entry()], releases, no_manifest)[0][0]
        self.assertTrue(without["description"].endswith("DeckyHub: audit and scans. Details: https://deckyhub.com/plugins/plug.html"))


if __name__ == "__main__":
    unittest.main()
