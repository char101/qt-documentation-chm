from io import StringIO
from contextlib import contextmanager
from os.path import splitext

class Buffer:
    def __init__(self, indent=0):
        self.buf = StringIO()
        self._indent = indent

    def line(self, text=None):
        if text is not None:
            self.buf.write(('\t' * self._indent) + text + '\n')
        else:
            self.buf.write('\n')

    @contextmanager
    def indent(self, ind=None):
        if ind is None:
            ind = self._indent + 1
        old_indent = self._indent
        self._indent = ind
        yield
        self._indent = old_indent

    def __str__(self):
        return self.buf.getvalue()

class Sitemap:
    # map from underscore key name to key name in the output file
    property_map = {}

    def __init__(self, **kwargs):
        self.properties = kwargs
        self.children = []

    def __setitem__(self, key, value):
        self.properties[key] = value

    def __getitem__(self, key):
        return self.properties[key]

    def serialize(self):
        b = Buffer()
        b.line('<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">')
        b.line('<HTML>')
        b.line('<HEAD>')
        b.line('<meta name="GENERATOR" content="Microsoft&reg; HTML Help Workshop 4.1">')
        b.line('<!-- Sitemap 1.0 -->')
        b.line('</HEAD><BODY>')
        if len(self.properties):
            b.line('<OBJECT type="text/site properties">')
            with b.indent():
                for k, v in self.properties.items():
                    if v is not None:
                        b.line('<param name="{}" value="{}">'.format(self.property_map.get(k, k), v))
            b.line('</OBJECT>')
        b.line('<UL>')
        with b.indent():
            for item in self.children:
                item.serialize(b)
        b.line('</UL>')
        b.line('</BODY></HTML>')
        print('Writing', self.filename)
        with open(self.filename, 'w') as f:
            f.write(str(b))

class Toc(Sitemap):
    property_map = {
        'image_type': 'ImageType',
        'window_styles': 'Window Styles',
        'font': 'Font'
    }

    def __init__(self, filename, **kwargs):
        kwargs.setdefault('image_type', 'Folder')
        super().__init__(**kwargs)
        self.filename = filename

    def append(self, name, local=None):
        item = TocItem(name, local)
        self.children.append(item)
        return item

class TocItem:
    def __init__(self, name, local=None):
        if name is None:
            raise Exception('Name should not be None')
        name = name.strip()
        if len(name) == 0:
            raise Exception('Name should not be an empty string')
        self.name = name
        self.local = local
        self.children = []

    def append(self, name, local=None):
        child = TocItem(name, local)
        self.children.append(child)
        return child

    def serialize(self, b):
        b.line('<LI> <OBJECT type="text/sitemap">')
        with b.indent():
            b.line('<param name="Name" value="{}">'.format(self.name))
            b.line('<param name="Local" value="{}">'.format(self.local))
            b.line('</OBJECT>')
        if len(self.children):
            b.line('<UL>')
            with b.indent():
                for child in self.children:
                    child.serialize(b)
            b.line('</UL>')

class Index(Sitemap):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.names = {}

    def append(self, name, local, title=None):
        if name in self.names:
            item = self.names[name]
            item.add_local(local, title)
        else:
            item = IndexItem(name, local, title)
            self.children.append(item)
            self.names[name] = item
        return item

    def serialize(self):
        """Make the keywords sorted in list"""
        self.children.sort(key=lambda item: item.name.lower())
        return super().serialize()

class IndexItem:
    def __init__(self, name, local, title=None):
        if name is None:
            raise Exception('Name should not be None')
        name = name.strip()
        if len(name) == 0:
            raise Exception('Name should not be an empty string')
        if local is None:
            raise Exception('Invalid local for {}'.format(name))
        if isinstance(local, str):
            local = [(local, title)]
        self.name = name
        self.local = local
        self.children = []
        self.children_names = {}

    def append(self, name, local, title=None):
        if name in self.children_names:
            child = self.children_names[name]
            child.add_local(local, title)
        else:
            child = IndexItem(name, local, title)
            self.children.append(child)
            self.children_names[name] = child
        return child

    def add_local(self, local, title=None):
        self.local.append((local, title))

    def serialize(self, b):
        b.line('<LI> <OBJECT type="text/sitemap">')
        with b.indent():
            b.line('<param name="Name" value="{}">'.format(self.name))
            for filename, title in self.local:
                if title:
                    b.line('<param name="Name" value="{}">'.format(title))
                b.line('<param name="Local" value="{}">'.format(filename))
            b.line('</OBJECT>')
        if len(self.children):
            b.line('<UL>')
            with b.indent():
                for child in self.children:
                    child.serialize(b)
            b.line('</UL>')

class Window:
    arguments = (
        'title',
        'contents_file',
        'index_file',
        'default_topic',
        'home',
        'jump1',
        'jump1_text',
        'jump2',
        'jump2_text',
        'navigation_pane_styles',
        'navigation_pane_width',
        'buttons',
        'initial_position',
        'style_flags',
        'extended_style_flags',
        'window_show_state',
        'navigation_pane_closed',
        'default_navigation_pane',
        'navigation_pane_position',
        'id'
    )

    def __init__(self, project, name, **kwargs):
        self.project = project
        self.name = name
        self.options = kwargs
        self.options.setdefault('id', 0)
        self.options.setdefault('navigation_pane_styles', '0x2120')
        self.options.setdefault('buttons', '0x3006')

    def _copy_project_options(self):
        keys = {
            'contents_file': 'contents_file',
            'index_file': 'index_file',
            'default_topic': 'default_topic',
            'default_topic': 'home'
        }
        for project_key, window_key in keys.items():
            if project_key in self.project:
                self.options.setdefault(window_key, self.project[project_key])

    def __setitem__(self, key, value):
        self.options[key] = value

    def __getitem__(self, key):
        return self.options[key]

    def __str__(self):
        self._copy_project_options()
        arguments = [self.options.get(arg, '') for arg in self.arguments]
        print(arguments)
        return '{}={}'.format(
            self.name,
            ','.join(self._quote(arg) for arg in arguments)
        )

    def _quote(self, val):
        if val is None or val == '':
            return ''
        if isinstance(val, int):
            return str(val)
        if val.isdigit() or val.startswith('0x'):
            return val
        return '"{}"'.format(val)

class Project:
    def __init__(self, filename, **kwargs):
        self.filename = filename
        self.files = []
        self.options = {
            'compatibility': '1.1 or later',
            'compiled_file': splitext(filename)[0] + '.chm',
            'display_compile_progress': 'No',
            'language': '0x409 English (United States)',
            'default_window': 'main',
            'binary_index': 'No',  # with binary index, multi topic keyword will not be displayed
        }
        self.window = Window(self, 'main')
        self.options.update(kwargs)

    def __setitem__(self, key, value):
        self.options[key] = value

    def __getitem__(self, key):
        return self.options[key]

    def __contains__(self, key):
        return key in self.options

    def append(self, filename):
        self.files.append(filename)

    def serialize(self):
        b = Buffer()
        b.line('[OPTIONS]')
        for k, v in sorted(self.options.items()):
            if v is not None:
                b.line('{}={}'.format(k.replace('_', ' ').capitalize(), v))
        b.line()
        b.line('[WINDOWS]')
        b.line(str(self.window))
        b.line()
        b.line()
        if len(self.files):
            b.line('[FILES]')
            for file in self.files:
                b.line(file)
            b.line()
        b.line('[INFOTYPES]')
        b.line()
        print('Writing', self.filename)
        with open(self.filename, 'w') as f:
            f.write(str(b))

class Chm:
    def __init__(self, name, compiled_file=None, default_topic='index.html', title=None):
        self.name = name
        self.project = Project(name + '.hhp', compiled_file=compiled_file)
        self.project['default_topic'] = default_topic
        if title:
            self.project.window['title'] = title
        self._toc = None
        self._index = None

    @property
    def toc(self):
        if self._toc is None:
            self._toc = Toc(self.name + '.hhc')
            self.project['contents_file'] = self.toc.filename
        return self._toc

    @property
    def index(self):
        if self._index is None:
            self._index = Index(self.name + '.hhk')
            self.project['index_file'] = self.index.filename
        return self._index

    def append(self, filename):
        self.project.append(filename)

    def save(self):
        self.project.serialize()
        if self._toc:
            self._toc.serialize()
        if self._index:
            self._index.serialize()

class DocChm(Chm):
    """Chm tailored for documentation with default settings"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project.window['navigation_pane_styles'] = '0x12120'  # show menu
        self.project.window['buttons'] = '0x10184e'  # without toolbar buttons, the font size menu doesn't work

        self.toc['image_type'] = None
        self.toc['window_styles'] = '0x801627'
        self.toc['font'] = 'Tahoma,8,0'
