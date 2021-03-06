#!/usr/bin/python2.7
# Generate a js file to include necessary depedencies (core and closure-compiler)
# This script generates blockly_uncompressed.js


import sys
if sys.version_info[0] != 2:
  raise Exception("Blockly build only compatible with Python 2.x.\n"
                  "You are using: " + sys.version)


import json, os, threading,re


def import_path(fullpath):
  """Import a file with full path specification.
  Allows one to import from any directory, something __import__ does not do.

  Args:
      fullpath:  Path and filename of import.

  Returns:
      An imported module.
  """
  path, filename = os.path.split(fullpath)
  filename, ext = os.path.splitext(filename)
  sys.path.append(path)
  module = __import__(filename)
  reload(module)  # Might be out of date.
  del sys.path[-1]
  return module



HEADER = ("// Do not edit this file; automatically generated by build.py.\n"
"'use strict';\n")




class Gen_uncompressed(threading.Thread):
  """Generate a JavaScript file that loads Blockly's raw files.
  Runs in a separate thread.
  """
  def __init__(self, search_paths, target_filename):
    threading.Thread.__init__(self)
    self.search_paths = search_paths
    self.target_filename = target_filename

  def run(self):
    f = open(self.target_filename, 'w')
    f.write(HEADER)
    f.write("""
this.IS_NODE_JS = !!(typeof module !== 'undefined' && module.exports);
this.BLOCKLY_DIR = (function(root) {
  if (!root.IS_NODE_JS) {
    // Find name of current directory.
    var scripts = document.getElementsByTagName('script');
    var re = new RegExp('(.+)[\/]blockly_(.*)uncompressed\.js$');
    for (var i = 0, script; script = scripts[i]; i++) {
      var match = re.exec(script.src);
      if (match) {
        return match[1];
      }
    }
    alert('Could not detect Blockly\\'s directory name.');
  }
  return '';
})(this);
this.BLOCKLY_BOOT = function(root) {
  if (root.IS_NODE_JS) {
    require('google-closure-library');
  } else if (typeof goog == 'undefined') {
    alert('Error: Closure not found.  Read this:\\n' +
          'developers.google.com/blockly/guides/modify/web/closure');
  }
  var dir = '';
  if (root.IS_NODE_JS) {
    dir = 'blockly';
  } else {
    dir = this.BLOCKLY_DIR.match(/[^\\/]+$/)[0];
  }
  // Execute after Closure has loaded.
""")
    add_dependency = []
    base_path = calcdeps.FindClosureBasePath(self.search_paths)
    for dep in calcdeps.BuildDependenciesFromFiles(self.search_paths):
      add_dependency.append(calcdeps.GetDepsLine(dep, base_path))
    add_dependency.sort()  # Deterministic build.
    add_dependency = '\n'.join(add_dependency)
    # Find the Blockly directory name and replace it with a JS variable.
    # This allows blockly_uncompressed.js to be compiled on one computer and be
    # used on another, even if the directory name differs.
    m = re.search('[\\/]([^\\/]+)[\\/]core[\\/]blockly.js', add_dependency)
    add_dependency = re.sub('([\\/])' + re.escape(m.group(1)) +
        '([\\/](core|accessible)[\\/])', '\\1" + dir + "\\2', add_dependency)
    f.write(add_dependency + '\n')

    provides = []
    for dep in calcdeps.BuildDependenciesFromFiles(self.search_paths):
      if not dep.filename.startswith(os.pardir + os.sep):  # '../'
        provides.extend(dep.provides)
    provides.sort()  # Deterministic build.
    f.write('\n')
    f.write('// Load Blockly.\n')
    for provide in provides:
      f.write("goog.require('%s');\n" % provide)

    f.write("""
delete root.BLOCKLY_DIR;
delete root.BLOCKLY_BOOT;
delete root.IS_NODE_JS;
};
if (this.IS_NODE_JS) {
  this.BLOCKLY_BOOT(this);
  module.exports = Blockly;
} else {
  // Delete any existing Closure (e.g. Soy's nogoog_shim).
  document.write('<script>var goog = undefined;</script>');
  // Load fresh Closure Library.
  document.write('<script src="' + this.BLOCKLY_DIR +
      '/../closure-library/closure/goog/base.js"></script>');
  document.write('<script>this.BLOCKLY_BOOT(this);</script>');
}
""")
    f.close()
    print("SUCCESS: " + self.target_filename)



if __name__ == "__main__":
  try:
    calcdeps = import_path(os.path.join(
        os.path.pardir, "closure-library", "closure", "bin", "calcdeps.py"))
  except ImportError:
    if os.path.isdir(os.path.join(os.path.pardir, "closure-library-read-only")):
      # Dir got renamed when Closure moved from Google Code to GitHub in 2014.
      print("Error: Closure directory needs to be renamed from"
            "'closure-library-read-only' to 'closure-library'.\n"
            "Please rename this directory.")
    elif os.path.isdir(os.path.join(os.path.pardir, "google-closure-library")):
      # When Closure is installed by npm, it is named "google-closure-library".
      #calcdeps = import_path(os.path.join(
      # os.path.pardir, "google-closure-library", "closure", "bin", "calcdeps.py"))
      print("Error: Closure directory needs to be renamed from"
           "'google-closure-library' to 'closure-library'.\n"
           "Please rename this directory.")
    else:
      print("""Error: Closure not found.  Read this:
developers.google.com/blockly/guides/modify/web/closure""")
    sys.exit(1)

  core_search_paths = calcdeps.ExpandDirectories(
      ["core","c_core",os.path.join(os.path.pardir, "closure-library")])
  core_search_paths.sort()  # Deterministic build.

  Gen_uncompressed(core_search_paths,"blockly_uncompressed.js").start()


