import unittest

from build_zohar_tudastar import parse_book, search_documents, tokens


def chapter(uid, body, title="Test", volume=1):
    return (
        f'<a id="source-{uid}"></a>\n\n### {title}\n\n'
        f"Path: Zohar for All / Vol. {volume} / {title}\n\n"
        "Language: en  \n"
        f"Source: https://kabbalahmedia.info/en/sources/{uid}?source_language=en  \n"
        "Official download: https://cdn.kabbalahmedia.info/test.docx\n\n"
        f"#### {title}\n\n{body}\n\n"
    )


class BookIndexTests(unittest.TestCase):
    def test_point_continuations_restarts_and_volume_boundaries(self):
        markdown = chapter("a", "20) First paragraph.\n\nContinuation.\n\n20) Restart.")
        markdown += "\n## Vol. 2\n\n" + chapter("b", "7) Last.", volume=2)
        markdown += "\n---\n\nVerified source entries: 2."
        chapters, points, bodies = parse_book(markdown)
        self.assertEqual(len(chapters), 2)
        self.assertEqual([point["id"] for point in points], ["a:20:1", "a:20:2", "b:7:1"])
        self.assertIn("Continuation.", points[0]["text"])
        self.assertNotIn("Vol. 2", points[1]["text"])
        self.assertNotIn("Verified source", points[2]["text"])
        self.assertEqual(chapters[0]["point_range"], [20, 20])
        self.assertEqual(bodies["a"]["points"], points[:2])

    def test_unnumbered_chapter_is_preserved_without_fake_point(self):
        chapters, points, bodies = parse_book(chapter("a", "Unnumbered explanation."))
        self.assertEqual(points, [])
        self.assertIsNone(chapters[0]["point_range"])
        self.assertIn("Unnumbered explanation.", bodies["a"]["preamble"])

    def test_unspaced_numbers_and_direction_mark_are_preserved(self):
        _, points, _ = parse_book(chapter("a", "30.\u200e Text.\n\n497.Unspaced.\n\n\u200e223) Hidden marker."))
        self.assertEqual([point["number"] for point in points], [30, 497, 223])
        self.assertEqual(points[0]["text"], "Text.")
        self.assertEqual(points[2]["text"], "Hidden marker.")

    def test_invalid_source_and_duplicate_chapter_are_errors(self):
        text = chapter("a", "1) Test.")
        with self.assertRaises(ValueError):
            parse_book(text.replace("kabbalahmedia.info/en", "example.com/en"))
        with self.assertRaises(ValueError):
            parse_book(text + text)

    def test_hungarian_synonyms_and_conjunction(self):
        pairs = [
            ("fény", "light"), ("edény/kli", "vessel vessel"),
            ("teremtő", "creator"), ("akarat/vágy", "desire desire"),
            ("képernyő", "screen"), ("visszaverődő fény", "reflected light"),
            ("teremtés célja", "purpose creation"),
        ]
        for hungarian, english in pairs:
            with self.subTest(hungarian=hungarian):
                self.assertEqual(tokens(hungarian), tokens(english))
        self.assertEqual(tokens("vagy"), [])
        self.assertEqual(tokens("vágyát"), ["desire"])
        self.assertNotEqual(tokens("kli"), tokens("klipot"))

    def test_public_search_data_discards_prose_and_original_word_order(self):
        first = parse_book(chapter("a", "1) Vessel light vessel creator."))
        reordered = parse_book(chapter("a", "1) Creator vessel vessel light."))
        public = search_documents(*first)
        self.assertEqual(public, search_documents(*reordered))
        documents, postings, lengths, keywords = public
        self.assertEqual(documents, [[0, 1, 1, "a:1:1"]])
        self.assertEqual(lengths, [5])
        self.assertEqual(keywords, [["vessel", "creator", "light", "test"]])
        self.assertTrue(all(isinstance(positions, list) for positions in postings.values()))
        self.assertNotIn("Vessel light vessel creator.", str(public))


if __name__ == "__main__":
    unittest.main()
