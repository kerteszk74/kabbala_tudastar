import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yt_dlp

import summarize_youtube as script


class DescriptionTests(unittest.TestCase):
    def setUp(self):
        self.analysis = script.Analysis(
            summary_sentences=["Első mondat.", "Második mondat.", "Harmadik mondat."],
            chapters=[
                script.Chapter(start_seconds=0, title="Bevezetés"),
                script.Chapter(start_seconds=10, title="Első rész"),
                script.Chapter(start_seconds=20, title="Második rész"),
            ],
            glossary=[script.GlossaryItem(term="Bina", explanation="Fogalom.")],
            hashtags=["#Kabbala", "#Zohár", "#Bina"],
        )

    def test_topics_share_one_link_and_hashtags_end_description(self):
        topics = [script.Topic(title, "") for title in ("Első", "Második", "Harmadik")]
        description = script.render_description(self.analysis, 30, topics)
        self.assertIn(
            "Kapcsolódó témák a Kabbala Tudástárban\n"
            "- Első\n- Második\n- Harmadik\n\n"
            f"Bővebben a Kabbala Tudástárban: {script.KNOWLEDGE_URL}",
            description,
        )
        self.assertEqual(description.count(script.KNOWLEDGE_URL), 1)
        self.assertTrue(description.endswith("#Kabbala #Zohár #Bina\n"))

    def test_hashtags_remain_when_no_topics_are_available(self):
        description = script.render_description(self.analysis, 30, [])
        self.assertNotIn(script.KNOWLEDGE_URL, description)
        self.assertTrue(description.endswith("#Kabbala #Zohár #Bina\n"))

    def test_hashtags_are_cleaned_and_deduplicated_in_description(self):
        data = self.analysis.model_dump()
        data["hashtags"] = [" #Kabbala Tanítás ", "#kabbalatanítás", "#Zohár!", "#123", "#Bnei_Baruch", "#Extra"]
        description = script.render_description(script.Analysis.model_validate(data), 30, [])
        self.assertTrue(description.endswith("#KabbalaTanítás #Zohár #123 #BneiBaruch\n"))

    def test_short_hashtag_lists_are_padded_without_duplicates(self):
        for hashtags, expected in (
            ([], "#Kabbala #Zohár #BneiBaruch"),
            (["#___", "#kabbala", "szöveg"], "#kabbala #Zohár #BneiBaruch"),
        ):
            with self.subTest(hashtags=hashtags):
                data = self.analysis.model_dump()
                data["hashtags"] = hashtags
                description = script.render_description(script.Analysis.model_validate(data), 30, [])
                self.assertEqual(description.splitlines()[-1], expected)


class YoutubeOptionsTests(unittest.TestCase):
    def test_options_are_accepted_by_installed_yt_dlp(self):
        with yt_dlp.YoutubeDL(script.youtube_options()) as downloader:
            self.assertIn("ejs:github", downloader.params["remote_components"])
            self.assertIn("deno", downloader.params["js_runtimes"])

    def test_options_are_used_for_listing_metadata_and_download(self):
        seen = []
        video_info = {
            "id": "abcdefghijk", "title": "Title", "duration": 30,
            "upload_date": "20260101",
        }

        class FakeDownloader:
            def __init__(self, options):
                self.options = options
                seen.append(options)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def extract_info(self, url, download):
                if download:
                    output = Path(self.options["outtmpl"].replace("%(ext)s", "mp3"))
                    output.write_bytes(b"audio")
                    return video_info
                if self.options.get("extract_flat"):
                    return {"entries": [{"id": video_info["id"]}]}
                return video_info

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(script.yt_dlp, "YoutubeDL", FakeDownloader), \
                    patch.object(script, "find_deno", return_value=r"C:\Tools\deno.exe"):
                videos, failures = script.select_videos("https://www.youtube.com/playlist?list=test", 1)
                audio = script.download_audio(videos[0], Path(directory), "ffmpeg")
            self.assertEqual(audio.read_bytes(), b"audio")

        self.assertFalse(failures)
        self.assertEqual(len(seen), 3)
        for options in seen:
            self.assertEqual(options["remote_components"], ["ejs:github"])
            self.assertEqual(options["js_runtimes"], {"deno": {"path": r"C:\Tools\deno.exe"}})
            self.assertEqual(options["retries"], 3)
            self.assertEqual(options["fragment_retries"], 3)
            self.assertEqual(options["sleep_interval"], 2)
            self.assertEqual(options["max_sleep_interval"], 5)
            self.assertEqual(options["extractor_args"], {"youtube": {"player_client": ["web", "mweb", "default"]}})
        self.assertEqual(seen[-1]["format"], "bestaudio/best")
        self.assertEqual(seen[-1]["postprocessors"][0]["key"], "FFmpegExtractAudio")

    def test_metadata_failure_does_not_prevent_later_video_selection(self):
        class FakeDownloader:
            def __init__(self, options):
                self.options = options

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def extract_info(self, url, download):
                if self.options.get("extract_flat"):
                    return {"entries": [
                        {"id": "abcdefghijk", "title": "Első"},
                        {"id": "ABCDEFGHIJK", "title": "Második"},
                    ]}
                if url.endswith("abcdefghijk"):
                    raise yt_dlp.utils.DownloadError("HTTP Error 403: Forbidden")
                return {"id": "ABCDEFGHIJK", "title": "Második", "duration": 30, "upload_date": "20260101"}

        with patch.object(script.yt_dlp, "YoutubeDL", FakeDownloader), \
                self.assertLogs(script.LOG, level="ERROR") as logs:
            videos, failures = script.select_videos("https://youtube.com/playlist?list=test", 2)
        self.assertEqual([video.id for video in videos], ["ABCDEFGHIJK"])
        self.assertEqual(len(failures), 1)
        self.assertTrue(any("Első" in line and "abcdefghijk" in line and "403" in line for line in logs.output))


class ExistingOutputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root_patch = patch.object(script, "ROOT", Path(directory.name))
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.videos = [
            script.Video("abcdefghijk", "Új cím", "https://youtu.be/abcdefghijk", 30, 2),
            script.Video("ABCDEFGHIJK", "Második", "https://youtu.be/ABCDEFGHIJK", 30, 1),
            script.Video("123456789ab", "Harmadik", "https://youtu.be/123456789ab", 30, 0),
        ]

    def test_only_matching_txt_files_count(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            self.assertFalse(script.has_output(self.videos[0], output / "missing"))
            (output / "old_abcdefghijk.md").write_text("", encoding="utf-8")
            (output / "old_abcdefghijk.txt.backup").write_text("", encoding="utf-8")
            (output / "abcdefghijk.txt").write_text("", encoding="utf-8")
            (output / "folder_abcdefghijk.txt").mkdir()
            self.assertFalse(script.has_output(self.videos[0], output))
            (output / "old_abcdefghijk.txt").write_text("", encoding="utf-8")
            self.assertTrue(script.has_output(self.videos[0], output))
            self.assertFalse(script.has_output(self.videos[1], output))
            with self.assertRaises(NotADirectoryError):
                script.has_output(self.videos[0], output / "old_abcdefghijk.txt")

    def test_limit_counts_skipped_videos_and_continues_to_next(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "Régi cím_abcdefghijk.txt").write_text("kész", encoding="utf-8")
            with patch.object(script, "select_videos", side_effect=lambda url, limit: (self.videos[:limit], [])) as select, \
                    patch.object(script.shutil, "which", return_value="ffmpeg"), \
                    patch.object(script.google.auth, "default", return_value=(object(), None)), \
                    patch.object(script, "KnowledgeIndex"), \
                    patch.object(script.genai, "Client"), \
                    patch.object(script, "process_video") as process, \
                    self.assertLogs(script.LOG, level="INFO") as logs:
                status = script.main(["--url", "https://youtube.com/@channel",
                                      "--out", str(output), "--limit", "2"])
            self.assertEqual(status, 0)
            select.assert_called_once_with("https://youtube.com/@channel", 2)
            self.assertEqual(process.call_count, 1)
            self.assertEqual(process.call_args.args[1], self.videos[1])
            self.assertTrue(any("Már elkészült, átugrás..." in line for line in logs.output))

    def test_all_skipped_needs_no_ffmpeg_or_adc(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "old_abcdefghijk.txt").write_text("kész", encoding="utf-8")
            with patch.object(script, "select_videos", return_value=(self.videos[:1], [])), \
                    patch.object(script.shutil, "which", return_value=None), \
                    patch.object(script.google.auth, "default") as auth, \
                    patch.object(script, "process_video") as process:
                self.assertEqual(script.main(["--url", self.videos[0].url, "--out", str(output)]), 0)
            auth.assert_not_called()
            process.assert_not_called()

    def test_force_processes_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "old_abcdefghijk.txt").write_text("kész", encoding="utf-8")
            with patch.object(script, "select_videos", return_value=(self.videos[:1], [])), \
                    patch.object(script.shutil, "which", return_value="ffmpeg"), \
                    patch.object(script.google.auth, "default", return_value=(object(), None)), \
                    patch.object(script, "KnowledgeIndex"), \
                    patch.object(script.genai, "Client"), \
                    patch.object(script, "process_video") as process:
                self.assertEqual(script.main(["--url", self.videos[0].url,
                                              "--out", str(output), "--force"]), 0)
            self.assertEqual(process.call_count, 1)

    def test_failure_continues_reports_and_sleeps_only_between_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "old_123456789ab.txt").write_text("kész", encoding="utf-8")

            def process_or_fail(client, video, destination, *args):
                if video == self.videos[0]:
                    raise RuntimeError("HTTP Error 403")
                script.save_description(video, "Új összefoglaló.\n", destination)

            with patch.object(script, "select_videos", return_value=(self.videos, [])), \
                    patch.object(script.shutil, "which", return_value="ffmpeg"), \
                    patch.object(script.google.auth, "default", return_value=(object(), None)), \
                    patch.object(script, "KnowledgeIndex"), \
                    patch.object(script.genai, "Client"), \
                    patch.object(script, "process_video", side_effect=process_or_fail) as process, \
                    patch.object(script.time, "sleep") as sleep, \
                    self.assertLogs(script.LOG, level="INFO") as logs:
                status = script.main(["--url", self.videos[0].url, "--out", str(output), "--limit", "3"])
        self.assertEqual(status, 1)
        self.assertEqual([call.args[1] for call in process.call_args_list], self.videos[:2])
        sleep.assert_called_once_with(3)
        self.assertTrue(any("Új cím" in line and "abcdefghijk" in line and "403" in line for line in logs.output))
        self.assertTrue(any("1 feldolgozott" in line and "1 átugrott" in line and "1 sikertelen" in line
                            for line in logs.output))
        self.assertIn("Összesen: **2 videó**", (script.ROOT / "INDEX.md").read_text(encoding="utf-8"))

    def test_metadata_only_failures_are_reported_without_initialization(self):
        failure = script.VideoFailure("Első", "abcdefghijk", "HTTP Error 403")
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(script, "select_videos", return_value=([], [failure])), \
                    patch.object(script.google.auth, "default") as auth, \
                    patch.object(script.time, "sleep") as sleep, \
                    self.assertLogs(script.LOG, level="INFO") as logs:
                status = script.main(["--url", self.videos[0].url, "--out", directory])
        self.assertEqual(status, 1)
        auth.assert_not_called()
        sleep.assert_not_called()
        self.assertTrue(any("Első" in line and "abcdefghijk" in line and "403" in line for line in logs.output))

    def test_failed_markdown_save_does_not_create_txt_completion_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.object(script.os, "replace", side_effect=OSError("write failed")):
                with self.assertRaises(OSError):
                    script.save_description(self.videos[0], "description", output)
            self.assertFalse(script.has_output(self.videos[0], output))

    def test_keyboard_interrupt_stops_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(script, "select_videos", return_value=(self.videos, [])), \
                    patch.object(script.shutil, "which", return_value="ffmpeg"), \
                    patch.object(script.google.auth, "default", return_value=(object(), None)), \
                    patch.object(script, "KnowledgeIndex"), \
                    patch.object(script.genai, "Client"), \
                    patch.object(script, "process_video", side_effect=KeyboardInterrupt) as process, \
                    patch.object(script.time, "sleep") as sleep:
                status = script.main(["--url", self.videos[0].url, "--out", directory, "--limit", "3"])
        self.assertEqual(status, 130)
        self.assertEqual(process.call_count, 1)
        sleep.assert_not_called()


class IndexTests(unittest.TestCase):
    def test_index_only_uses_local_summaries_and_groups_formats_by_video_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            video = script.Video("a_bcDE-fgH1", "Ékezet [A]", "", 30, 0)
            description = (
                "Első | bekezdés,\nfolytatás.\n\nIdőbélyeges tartalomjegyzék\n00:00 Rész\n\n"
                "Kulcsfogalmak és kabbalisztikus szótár\n- Bina: Magyarázat.\n- Kli: Edény.\n\n"
                "#Kabbala #Zohár #BneiBaruch\n"
            )
            script.save_description(video, description, output)
            stale = output / f"Régi cím_{video.id}.txt"
            stale.write_text("Régi szöveg.", encoding="utf-8")
            os.utime(stale, (1, 1))
            (output / "Csak MD_abcdefghijk.md").write_text("Önálló bekezdés.", encoding="utf-8")
            (output / "üres_123456789ab.txt").touch()
            (output / "jegyzet.txt").write_text("Nem videó.", encoding="utf-8")

            with patch.object(script, "ROOT", root), \
                    patch.object(script, "select_videos") as select, \
                    patch.object(script.google.auth, "default") as auth, \
                    patch.object(script.shutil, "which") as find_tool:
                self.assertEqual(script.main(["--index-only"]), 0)
            select.assert_not_called()
            auth.assert_not_called()
            find_tool.assert_not_called()
            index = (root / "INDEX.md").read_text(encoding="utf-8")

        self.assertIn("Összesen: **2 videó**", index)
        self.assertIn(f"[Kabbala Tudástár]({script.KNOWLEDGE_URL})", index)
        self.assertEqual(index.count(f"watch?v={video.id}"), 1)
        for label in ("TXT", "MD"):
            self.assertIn(f"[{label}](output/%C3%89kezet%20%5BA%5D_{video.id}.{label.lower()})", index)
        self.assertIn("[MD](output/Csak%20MD_abcdefghijk.md)", index)
        self.assertNotIn("[TXT](output/Csak%20MD_", index)
        self.assertIn(r"Ékezet \[A\]", index)
        self.assertIn(r"| Bina, Kli | Első \| bekezdés, folytatás. |", index)
        for unwanted in ("Régi", "Nem videó", "Magyarázat", "Időbélyeges"):
            self.assertNotIn(unwanted, index)


if __name__ == "__main__":
    unittest.main()
