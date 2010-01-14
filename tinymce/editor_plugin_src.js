// A bunch of editor controls for wikis.

(function() {
  tinymce.create('tinymce.plugins.WikiPlugin', {
    init: function(ed, url) {
      // tinymce command, browser command, is ui elem?, cmd argument, title
      commands = [['b', 'Bold', false, '', 'bold'],
                  ['i', 'Italic', false, '', 'italics'],
                  ['u', 'Underline', false, '', 'underline'],
                  ['indent', 'Indent', false, '', 'indent'],
                  ['outdent', 'Outdent', false, '', 'outdent'],
                  ['listnum', 'InsertOrderedList', false, '', 'numbered list'],
                  ['list', 'InsertUnorderedList', false, '', 'bulleted list'],
                  ['hr', 'InsertHorizontalRule', false, '',
                   'insert horizontal line']];

      mk_command = function(name, cmd, ui_elem, arg) {
        return function() {
          ed.execCommand(cmd, ui_elem, arg);
          // TODO(marius): figure this one out.
          // ed.setActive(name, !ed.isActive(name));
        };
      };

      mk_on_nodechange = function(name, c) {
        return function(ed, cm, n) {
          cm.setActive(name, ed.queryCommandState(c[1]));
        };
      };

      for (var i = 0; i < commands.length; i++) {
        var c = commands[i];
        var name = 'wiki_' + c[0];
        ed.addCommand(name, mk_command(name, c[1], c[2], c[3]));
        ed.addButton(name, {
          title: c[4],
	  cmd: name,
          'class': name
        });

        ed.onNodeChange.add(mk_on_nodechange(name, c));
      }

      var js_commands = [['wiki_img', 'insert image'],
                         ['wiki_link', 'insert link or create page'],
                         ['wiki_switch', 'switch to wiki markup editor']];

      var mk_command = function(c) {
        if (c == 'wiki_link') {
          return function() {
            // This stuff is kind of nasty. If we have
            // other 2-state js commands, we should
            // generalize it.

            cmd = ed.controlManager.get('wiki_link');
            a = cmd.isActive();

            if (!!a) {
              ed.execCommand('unlink', false, '');
            } else {
              eval(ed.getParam(c, "function(ed) {};"))(ed);
            }

            cmd.setActive(!a);
          };
        } else {
          return function() {
            eval(ed.getParam(c, "function(ed) {};"))(ed);
          };
        }
      };

      for (var i = 0; i < js_commands.length; i++) {
        var c = js_commands[i][0];
        var tip = js_commands[i][1];

        ed.addCommand(c, mk_command(c));
        ed.addButton(c, {
          title: tip,
	  cmd: c,
          'class': c
        });
      }

      // Now take care of linking.
      ed.onNodeChange.add(function(ed, cm, n) {
        var a = tinymce.DOM.getParent(n, 'A');
        var c = cm.get('wiki_link');
	var c_n = tinymce.DOM.get(c.id);

        if (!!a) {
          // Activate unlink button.
          tinymce.DOM.addClass(c_n, 'wiki_breaklink');
          tinymce.DOM.removeClass(c_n, 'wiki_link');
        } else {
          tinymce.DOM.addClass(c_n, 'wiki_link');
          tinymce.DOM.removeClass(c_n, 'wiki_breaklink');
        }

        c.setActive(!!a);
      });

      ed.onInit.add(function() {
        ed.onNodeChange.add(
          function(ed, cm) {
	    tinymce.each(commands, function(c) {
              var cmd = 'wiki_' + c[0];
              var cmd_ = cm.get(cmd.toLowerCase());
              if (cmd_ !== undefined)
                cmd_.setActive(ed.queryCommandState(c[1]));
            });
	  });
      });
    },

    createControl : function(n, cm) {
      return null;
    },

    getInfo : function() {
      return {
        longname  : 'Wiki',
        author    : 'mixerlabs',
        authorurl : 'http://townme.com/',
        infourl   : 'http://townme.com/',
        version   : "1.0"
      };
    }});

   // Register plugin
   tinymce.PluginManager.add('wiki', tinymce.plugins.WikiPlugin);
 })();
