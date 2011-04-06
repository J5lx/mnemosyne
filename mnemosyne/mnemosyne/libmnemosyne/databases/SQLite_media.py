#
# SQLite_media.py <Peter.Bienstman@UGent.be>
#

import os
import re

from mnemosyne.libmnemosyne.utils import copy_file_to_dir
from mnemosyne.libmnemosyne.utils import expand_path, contract_path

re_src = re.compile(r"""src=['\"](.+?)['\"]""", re.DOTALL | re.IGNORECASE)


class SQLiteMedia(object):

    """Code to be injected into the SQLite database class through inheritance,
    so that SQLite.py does not becomes too large.


    """
            
    def media_dir(self):
        return unicode(os.path.join(self.config().data_dir,
            os.path.basename(self.config()["path"]) + "_media"))

    def fact_contains_static_media_files(self, fact):
        # Could be part of fact.py, but is put here to have all media related
        # functions in one place.
        return re_src.search("".join(fact.data.values())) != None

    def _media_hash(self, filename):

        """A hash function that will be used to determine whether or not a
        media file has been modified outside of Mnemosyne.

        'filename' is a relative path inside the media dir.

        In the current implementation, we use the modification date for this.
        Although less robust, modification dates are faster to lookup then
        calculating a hash, especially on mobile devices.

        In principle, you could have different hash implementations on
        different systems, as the hash is considered something internal and is
        not sent across during sync e.g.

        """
        
        return str(os.path.getmtime(os.path.join(self.media_dir(),
            os.path.normcase(filename))))

    def check_for_edited_media_files(self):
        # Regular media files.
        new_hashes = {}
        for sql_res in self.con.execute("select * from media"):
            filename = sql_res["filename"]
            if not os.path.exists(expand_path(filename, self.media_dir())):
                continue
            new_hash = self._media_hash(filename)
            if sql_res["_hash"] != new_hash:
                new_hashes[filename] = new_hash
        for filename, new_hash in new_hashes.iteritems():
            self.con.execute("update media set _hash=? where filename=?",
                (new_hash, filename))
            self.log().edited_media_file(filename)
        # Other media files, e.g. latex.
        for cursor in self.con.execute("select value from data_for_fact"):
            for f in self.component_manager.all("hook",
                "check_for_edited_local_media_files"):
                f.run(cursor[0])
    
    def _process_media(self, fact):

        """Copy the media files to the media directory and edit the media
        table. We don't keep track of which facts use which media and delete
        a media file if it's no longer in use. The reason for this is that some
        people use the media directory as their only location to store their
        media files, and also use these files for other purposes.
        
        When we are applying log entries during sync, we should not generate
        extra log entries, this will be taken care of by the syncing
        algorithm. (Not all 'added_media_file' events originated here, they are
        also generated by the latex subsystem, or by checking for files which
        were modified outside of Mnemosyne.

        """

        for match in re_src.finditer("".join(fact.data.values())):
            filename = match.group(1)
            # If needed, copy file to the media dir. Normally this happens when
            # the user clicks 'Add image' e.g., but he could have typed in the
            # full path directly.
            if os.path.isabs(filename):
                filename = copy_file_to_dir(filename, self.media_dir())
            else:  # We always store Unix paths internally.
                filename = filename.replace("\\", "/")
            for key, value in fact.data.iteritems():
                fact.data[key] = value.replace(match.group(1), filename)
                self.con.execute("""update data_for_fact set value=? where
                    _fact_id=? and key=?""", (fact.data[key], fact._id, key))
            if self.con.execute("select count() from media where filename=?",
                                (filename, )).fetchone()[0] == 0:
                self.con.execute("""insert into media(filename, _hash)
                    values(?,?)""", (filename, self._media_hash(filename)))
                if not self.syncing:
                    self.log().added_media_file(filename)

    def clean_orphaned_static_media_files(self):
        
        """Remove the static (i.e. explictly specified in a src='' tag) unused
        media files.
        
        (This check takes less than 30 ms for 9000 cards with 400 media files on
        a 2.1 GHz dual core.)
        
        Note: purging dynamicly generated media files, like e.g. latex files,
        would be rather time consuming. These files are typically small anyway
        and can be easily cleaned up by deleting the entire _latex directory.

        """

        # Files referenced in the database.
        files_in_db = set()
        for result in self.con.execute(\
            "select value from data_for_fact where value like '%src=%'"):
            for match in re_src.finditer(result[0]):
                files_in_db.add(match.group(1))
        # Files in the media dir.
        files_in_media_dir = set()
        for root, dirnames, filenames in os.walk(self.media_dir()):
            root = contract_path(root, self.media_dir())
            if root.startswith("_"):
                continue
            for filename in filenames:
                # Paths are stored using unix convention.
                if root:
                    filename = root + "/" + filename
                files_in_media_dir.add(filename)
        # Delete orphaned files.
        for filename in files_in_media_dir - files_in_db:
            os.remove(expand_path(filename, self.media_dir()))
            self.log().deleted_media_file(filename)
        # Purge empty dirs.
        for root, dirnames, filenames in \
            os.walk(self.media_dir(), topdown=False):
            contracted_root = contract_path(root, self.media_dir())
            if not contracted_root or contracted_root.startswith("_"):
                continue
            if len(filenames) == 0 and len(dirnames) == 0:
                os.rmdir(root)


    
