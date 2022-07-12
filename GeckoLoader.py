#!/usr/bin/env python3
# Written by JoshuaMK 2020

import shutil
import sys
import tempfile
from pathlib import Path

from .dolreader import DolFile
from .fileutils import resource_path
from .kernel import CodeHandler, KernelLoader
from .tools import CommandLineParser, color_text

try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
    TRESET = Style.RESET_ALL
    TGREEN = Fore.GREEN
    TGREENLIT = Style.BRIGHT + Fore.GREEN
    TYELLOW = Fore.YELLOW
    TYELLOWLIT = Style.BRIGHT + Fore.YELLOW
    TRED = Fore.RED
    TREDLIT = Style.BRIGHT + Fore.RED

except ImportError:
    TRESET = ''
    TGREEN = ''
    TGREENLIT = ''
    TYELLOW = ''
    TYELLOWLIT = ''
    TRED = ''
    TREDLIT = ''

__version__ = "v7.1.0 (command line only)"


def clean_tmp_resources():
    with tempfile.TemporaryDirectory(prefix="GeckoLoader-") as tmpdir:
        system_tmpdir = Path(tmpdir).parent
    for entry in system_tmpdir.iterdir():
        if entry.name.startswith("GeckoLoader-"):
            shutil.rmtree(entry, ignore_errors=True)


class GeckoLoaderCli(CommandLineParser):

    def __init__(self, name, version=None, description=''):
        super().__init__(prog=(f"{name} {version}"),
                         description=description, allow_abbrev=False)
        self.__version__ = version
        self.__doc__ = description

        self.add_argument('dolfile', help='DOL file')
        self.add_argument('codelist', help='Folder or Gecko GCT|TXT file')
        self.add_argument('-a', '--alloc',
                          help='Define the size of the code allocation in hex, only applies when using the ARENA space',
                          metavar='SIZE')
        self.add_argument('-i', '--init',
                          help='Define where GeckoLoader is initialized in hex',
                          metavar='ADDRESS')
        self.add_argument('-tc', '--txtcodes',
                          help='''["ACTIVE", "ALL"] What codes get parsed when a txt file is used.
                        "ALL" makes all codes get parsed,
                        "ACTIVE" makes only activated codes get parsed.
                        "ACTIVE" is the default''',
                          default='ACTIVE',
                          metavar='TYPE')
        self.add_argument('--handler',
                          help='''["MINI", "FULL"] Which codehandler gets used. "MINI" uses a smaller codehandler
                        which only supports (0x, 2x, Cx, and E0 types) and supports up to
                        600 lines of gecko codes when using the legacy codespace.
                        "FULL" is the standard codehandler, supporting up to 350 lines of code
                        in the legacy codespace. "FULL" is the default''',
                          default='FULL',
                          choices=['MINI', 'FULL'],
                          metavar='TYPE')
        self.add_argument('--hooktype',
                          help='''["VI", "GX", "PAD"] The type of hook used for the RAM search. "VI" or "GX" are recommended,
                        although "PAD" can work just as well. "VI" is the default''',
                          default='VI',
                          choices=['VI', 'GX', 'PAD'],
                          metavar='HOOK')
        self.add_argument('--hookaddress',
                          help='Choose where the codehandler hooks to in hex, overrides auto hooks',
                          metavar='ADDRESS')
        self.add_argument('-o', '--optimize',
                          help='''Optimizes the codelist by directly patching qualifying
                        ram writes into the dol file, and removing them from the codelist''',
                          action='store_true')
        self.add_argument('-p', '--protect',
                          help='''Targets and nullifies the standard codehandler provided by loaders and Dolphin Emulator,
                        only applies when the ARENA is used''',
                          action='store_true')
        self.add_argument('--dest',
                          help='Target path to put the modified DOL, can be a folder or file',
                          metavar='PATH')
        self.add_argument('--splash',
                          help='''Print the splash screen, this option overrides
                        all other commands''',
                          action='store_true')
        self.add_argument('--encrypt',
                          help='Encrypts the codelist on compile time, helping to slow the snoopers',
                          action='store_true')
        self.add_argument('-q', '--quiet',
                          help='Print nothing to the console',
                          action='store_true')
        self.add_argument('-v', '--verbose',
                          help='Print extra info to the console',
                          default=0,
                          action='count')

    def __str__(self) -> str:
        return self.__doc__

    def print_splash(self):
        helpMessage = 'Try option -h for more info on this program'.center(
            64, ' ')
        version = self.__version__.rjust(9, ' ')

        logo = ['                                                                ',
                ' ╔═══════════════════════════════════════════════════════════╗  ',
                ' ║                                                           ║  ',
                ' ║  ┌───┐┌───┐┌───┐┌┐┌─┐┌───┐┌┐   ┌───┐┌───┐┌───┐┌───┐┌───┐  ║  ',
                ' ║  │┌─┐││┌──┘│┌─┐││││┌┘│┌─┐│││   │┌─┐││┌─┐│└┐┌┐││┌──┘│┌─┐│  ║  ',
                ' ║  ││ └┘│└──┐││ └┘│└┘┘ ││ ││││   ││ ││││ ││ │││││└──┐│└─┘│  ║  ',
                ' ║  ││┌─┐│┌──┘││ ┌┐│┌┐│ ││ ││││ ┌┐││ │││└─┘│ │││││┌──┘│┌┐┌┘  ║  ',
                ' ║  │└┴─││└──┐│└─┘││││└┐│└─┘││└─┘││└─┘││┌─┐│┌┘└┘││└──┐│││└┐  ║  ',
                ' ║  └───┘└───┘└───┘└┘└─┘└───┘└───┘└───┘└┘ └┘└───┘└───┘└┘└─┘  ║  ',
                ' ║                                                           ║  ',
                ' ║           ┌┐┌───┐┌───┐┌┐ ┌┐┌┐ ┌┐┌───┐┌─┐┌─┐┌┐┌─┐          ║  ',
                ' ║           │││┌─┐││┌─┐│││ ││││ │││┌─┐││ └┘ ││││┌┘          ║  ',
                ' ║           ││││ │││└──┐│└─┘│││ ││││ │││┌┐┌┐││└┘┘           ║  ',
                ' ║     ┌──┐┌┐││││ ││└──┐││┌─┐│││ │││└─┘││││││││┌┐│ ┌──┐      ║  ',
                ' ║     └──┘│└┘││└─┘││└─┘│││ │││└─┘││┌─┐││││││││││└┐└──┘      ║  ',
                ' ║         └──┘└───┘└───┘└┘ └┘└───┘└┘ └┘└┘└┘└┘└┘└─┘          ║  ',
                f' ║ {version: >57} ║  ',
                ' ╚═══════════════════════════════════════════════════════════╝  ',
                '                                                                ',
                '        GeckoLoader is a cli tool for allowing extended         ',
                '           gecko code space in all Wii and GC games.            ',
                '                                                                ',
                f'{helpMessage}',
                '                                                                ']

        for line in logo:
            print(color_text(
                line, [('║', TREDLIT), ('╔╚╝╗═', TRED)], TGREENLIT))

    def _validate_args(self, args) -> dict:
        dolFile = Path(args.dolfile).resolve()
        codeList = Path(args.codelist).resolve()

        if args.dest:
            dest = Path(args.dest).resolve()
            if dest.suffix == "":
                dest = dest / dolFile.name
        else:
            dest = Path.cwd() / "geckoloader-build" / dolFile.name

        if args.alloc:
            try:
                _allocation = int(args.alloc, 16)
            except ValueError:
                self.error(color_text(
                    'The allocation was invalid\n', defaultColor=TREDLIT))
        else:
            _allocation = None

        if args.hookaddress:
            if 0x80000000 > int(args.hookaddress, 16) >= 0x81800000:
                self.error(color_text(
                    'The codehandler hook address was beyond bounds\n', defaultColor=TREDLIT))
            else:
                try:
                    _codehook = int(args.hookaddress, 16)
                except ValueError:
                    self.error(color_text(
                        'The codehandler hook address was invalid\n', defaultColor=TREDLIT))
        else:
            _codehook = None

        if args.handler == CodeHandler.Types.MINI:
            codeHandlerFile = Path('bin/codehandler-mini.bin')
        elif args.handler == CodeHandler.Types.FULL:
            codeHandlerFile = Path('bin/codehandler.bin')
        else:
            self.error(color_text(
                f'Codehandler type {args.handler} is invalid\n', defaultColor=TREDLIT))

        if not dolFile.is_file():
            self.error(color_text(
                f'File "{dolFile}" does not exist\n', defaultColor=TREDLIT))

        if not codeList.exists():
            self.error(color_text(
                f'File/folder "{codeList}" does not exist\n', defaultColor=TREDLIT))

        return {"dol":         dolFile,
                "codepath":    codeList,
                "codehandler": codeHandlerFile,
                "destination": dest,
                "allocation":  _allocation,
                "hookaddress": _codehook,
                "hooktype":    args.hooktype,
                "initaddress": None if args.init is None else int(args.init, 16),
                "includeall":  args.txtcodes.lower() == "all",
                "optimize":    args.optimize,
                "protect":     args.protect,
                "encrypt":     args.encrypt,
                "verbosity":   args.verbose,
                "quiet":       args.quiet}

    def _exec(self, args, tmpdir):
        context = self._validate_args(args)

        tmpdir = Path(tmpdir)

        try:
            with context["dol"].open("rb") as dol:
                dolFile = DolFile(dol)

            with resource_path(context["codehandler"]).open("rb") as handler:
                codeHandler = CodeHandler(handler)
                codeHandler.allocation = context["allocation"]
                codeHandler.hookAddress = context["hookaddress"]
                codeHandler.hookType = context["hooktype"]
                codeHandler.includeAll = context["includeall"]
                codeHandler.optimizeList = context["optimize"]

            with resource_path("bin/geckoloader.bin").open("rb") as kernelfile:
                geckoKernel = KernelLoader(kernelfile, self)
                geckoKernel.initAddress = context["initaddress"]
                geckoKernel.verbosity = context["verbosity"]
                geckoKernel.quiet = context["quiet"]
                geckoKernel.encrypt = context["encrypt"]
                geckoKernel.protect = context["protect"]

            if not context["destination"].parent.exists():
                context["destination"].parent.mkdir(parents=True, exist_ok=True)

            geckoKernel.build(context["codepath"], dolFile,
                              codeHandler, tmpdir, context["destination"])

        except FileNotFoundError as e:
            self.error(color_text(e, defaultColor=TREDLIT))


if __name__ == "__main__":
    clean_tmp_resources()

    cli = GeckoLoaderCli('GeckoLoader', __version__,
                         description='Dol editing tool for allocating extended codespace')

    if '--splash' in sys.argv:
        cli.print_splash()
    else:
        args = cli.parse_args()
        with tempfile.TemporaryDirectory(prefix="GeckoLoader-") as tmpdir:
            cli._exec(args, tmpdir)
