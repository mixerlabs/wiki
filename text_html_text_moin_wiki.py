"""
    Originally taken from MoinMoin 1.8.1,
    MoinMoin/converter/text_html_text_moin_wiki.py

    MoinMoin - convert from html to wiki markup

    @copyright: 2005-2006 Bastian Blank, Florian Festi, Reimar Bauer,
                2005-2007 MoinMoin:ThomasWaldmann
    @license: GNU GPL, see COPYING for details.
"""

import re, os
import xml.dom.minidom # HINT: the nodes in parse result tree need .has_key(), "x in ..." does not work
import urllib
from xml.dom import Node

from util import *
from util.functional import switch

from django.core.exceptions import ObjectDoesNotExist
from www.wiki.models import Wiki
from www.wiki.render import (default_thumb_width, max_image_width,
        parse_img_attributes)
import urlparse
import cgi

class wikiutil:
    # TODO(marius)
    @staticmethod
    def resolve_interwiki(wikiname, pagename):
        """ @return: (wikitag, wikiurl, wikitail, err)"""
        return (wikiname, '/', "/InterWiki", True)

    @staticmethod
    def url_unquote(s, want_unicode=True):
        return urllib.unquote(s)
    
    @staticmethod
    def pagelinkmarkup(pagename, text=None):
        """ return markup that can be used as link to page <pagename> """
        return 'TODO'
#         from MoinMoin.parser.text_moin_wiki import Parser
#         if re.match(Parser.word_rule + "$", pagename, re.U|re.X) and \
#                (text is None or text == pagename):
#             return pagename
#         else:
#             if text is None or text == pagename:
#                 text = ''
#             else:
#                 text = '|%s' % text
#                 return u'[[%s%s]]' % (pagename, text)


class ConvertError(Exception): pass

chars_upper = u"\u0041\u0042\u0043\u0044\u0045\u0046\u0047\u0048\u0049\u004a\u004b\u004c\u004d\u004e\u004f\u0050\u0051\u0052\u0053\u0054\u0055\u0056\u0057\u0058\u0059\u005a\u00c0\u00c1\u00c2\u00c3\u00c4\u00c5\u00c6\u00c7\u00c8\u00c9\u00ca\u00cb\u00cc\u00cd\u00ce\u00cf\u00d0\u00d1\u00d2\u00d3\u00d4\u00d5\u00d6\u00d8\u00d9\u00da\u00db\u00dc\u00dd\u00de\u0100\u0102\u0104\u0106\u0108\u010a\u010c\u010e\u0110\u0112\u0114\u0116\u0118\u011a\u011c\u011e\u0120\u0122\u0124\u0126\u0128\u012a\u012c\u012e\u0130\u0132\u0134\u0136\u0139\u013b\u013d\u013f\u0141\u0143\u0145\u0147\u014a\u014c\u014e\u0150\u0152\u0154\u0156\u0158\u015a\u015c\u015e\u0160\u0162\u0164\u0166\u0168\u016a\u016c\u016e\u0170\u0172\u0174\u0176\u0178\u0179\u017b\u017d\u0181\u0182\u0184\u0186\u0187\u0189\u018a\u018b\u018e\u018f\u0190\u0191\u0193\u0194\u0196\u0197\u0198\u019c\u019d\u019f\u01a0\u01a2\u01a4\u01a6\u01a7\u01a9\u01ac\u01ae\u01af\u01b1\u01b2\u01b3\u01b5\u01b7\u01b8\u01bc\u01c4\u01c7\u01ca\u01cd\u01cf\u01d1\u01d3\u01d5\u01d7\u01d9\u01db\u01de\u01e0\u01e2\u01e4\u01e6\u01e8\u01ea\u01ec\u01ee\u01f1\u01f4\u01f6\u01f7\u01f8\u01fa\u01fc\u01fe\u0200\u0202\u0204\u0206\u0208\u020a\u020c\u020e\u0210\u0212\u0214\u0216\u0218\u021a\u021c\u021e\u0220\u0222\u0224\u0226\u0228\u022a\u022c\u022e\u0230\u0232\u0386\u0388\u0389\u038a\u038c\u038e\u038f\u0391\u0392\u0393\u0394\u0395\u0396\u0397\u0398\u0399\u039a\u039b\u039c\u039d\u039e\u039f\u03a0\u03a1\u03a3\u03a4\u03a5\u03a6\u03a7\u03a8\u03a9\u03aa\u03ab\u03d2\u03d3\u03d4\u03d8\u03da\u03dc\u03de\u03e0\u03e2\u03e4\u03e6\u03e8\u03ea\u03ec\u03ee\u03f4\u0400\u0401\u0402\u0403\u0404\u0405\u0406\u0407\u0408\u0409\u040a\u040b\u040c\u040d\u040e\u040f\u0410\u0411\u0412\u0413\u0414\u0415\u0416\u0417\u0418\u0419\u041a\u041b\u041c\u041d\u041e\u041f\u0420\u0421\u0422\u0423\u0424\u0425\u0426\u0427\u0428\u0429\u042a\u042b\u042c\u042d\u042e\u042f\u0460\u0462\u0464\u0466\u0468\u046a\u046c\u046e\u0470\u0472\u0474\u0476\u0478\u047a\u047c\u047e\u0480\u048a\u048c\u048e\u0490\u0492\u0494\u0496\u0498\u049a\u049c\u049e\u04a0\u04a2\u04a4\u04a6\u04a8\u04aa\u04ac\u04ae\u04b0\u04b2\u04b4\u04b6\u04b8\u04ba\u04bc\u04be\u04c0\u04c1\u04c3\u04c5\u04c7\u04c9\u04cb\u04cd\u04d0\u04d2\u04d4\u04d6\u04d8\u04da\u04dc\u04de\u04e0\u04e2\u04e4\u04e6\u04e8\u04ea\u04ec\u04ee\u04f0\u04f2\u04f4\u04f8\u0500\u0502\u0504\u0506\u0508\u050a\u050c\u050e\u0531\u0532\u0533\u0534\u0535\u0536\u0537\u0538\u0539\u053a\u053b\u053c\u053d\u053e\u053f\u0540\u0541\u0542\u0543\u0544\u0545\u0546\u0547\u0548\u0549\u054a\u054b\u054c\u054d\u054e\u054f\u0550\u0551\u0552\u0553\u0554\u0555\u0556\u10a0\u10a1\u10a2\u10a3\u10a4\u10a5\u10a6\u10a7\u10a8\u10a9\u10aa\u10ab\u10ac\u10ad\u10ae\u10af\u10b0\u10b1\u10b2\u10b3\u10b4\u10b5\u10b6\u10b7\u10b8\u10b9\u10ba\u10bb\u10bc\u10bd\u10be\u10bf\u10c0\u10c1\u10c2\u10c3\u10c4\u10c5\u1e00\u1e02\u1e04\u1e06\u1e08\u1e0a\u1e0c\u1e0e\u1e10\u1e12\u1e14\u1e16\u1e18\u1e1a\u1e1c\u1e1e\u1e20\u1e22\u1e24\u1e26\u1e28\u1e2a\u1e2c\u1e2e\u1e30\u1e32\u1e34\u1e36\u1e38\u1e3a\u1e3c\u1e3e\u1e40\u1e42\u1e44\u1e46\u1e48\u1e4a\u1e4c\u1e4e\u1e50\u1e52\u1e54\u1e56\u1e58\u1e5a\u1e5c\u1e5e\u1e60\u1e62\u1e64\u1e66\u1e68\u1e6a\u1e6c\u1e6e\u1e70\u1e72\u1e74\u1e76\u1e78\u1e7a\u1e7c\u1e7e\u1e80\u1e82\u1e84\u1e86\u1e88\u1e8a\u1e8c\u1e8e\u1e90\u1e92\u1e94\u1ea0\u1ea2\u1ea4\u1ea6\u1ea8\u1eaa\u1eac\u1eae\u1eb0\u1eb2\u1eb4\u1eb6\u1eb8\u1eba\u1ebc\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6\u1ec8\u1eca\u1ecc\u1ece\u1ed0\u1ed2\u1ed4\u1ed6\u1ed8\u1eda\u1edc\u1ede\u1ee0\u1ee2\u1ee4\u1ee6\u1ee8\u1eea\u1eec\u1eee\u1ef0\u1ef2\u1ef4\u1ef6\u1ef8\u1f08\u1f09\u1f0a\u1f0b\u1f0c\u1f0d\u1f0e\u1f0f\u1f18\u1f19\u1f1a\u1f1b\u1f1c\u1f1d\u1f28\u1f29\u1f2a\u1f2b\u1f2c\u1f2d\u1f2e\u1f2f\u1f38\u1f39\u1f3a\u1f3b\u1f3c\u1f3d\u1f3e\u1f3f\u1f48\u1f49\u1f4a\u1f4b\u1f4c\u1f4d\u1f59\u1f5b\u1f5d\u1f5f\u1f68\u1f69\u1f6a\u1f6b\u1f6c\u1f6d\u1f6e\u1f6f\u1fb8\u1fb9\u1fba\u1fbb\u1fc8\u1fc9\u1fca\u1fcb\u1fd8\u1fd9\u1fda\u1fdb\u1fe8\u1fe9\u1fea\u1feb\u1fec\u1ff8\u1ff9\u1ffa\u1ffb\u2102\u2107\u210b\u210c\u210d\u2110\u2111\u2112\u2115\u2119\u211a\u211b\u211c\u211d\u2124\u2126\u2128\u212a\u212b\u212c\u212d\u2130\u2131\u2133\u213e\u213f\u2145\uff21\uff22\uff23\uff24\uff25\uff26\uff27\uff28\uff29\uff2a\uff2b\uff2c\uff2d\uff2e\uff2f\uff30\uff31\uff32\uff33\uff34\uff35\uff36\uff37\uff38\uff39\uff3a"
chars_lower = u"\u0061\u0062\u0063\u0064\u0065\u0066\u0067\u0068\u0069\u006a\u006b\u006c\u006d\u006e\u006f\u0070\u0071\u0072\u0073\u0074\u0075\u0076\u0077\u0078\u0079\u007a\u00aa\u00b5\u00ba\u00df\u00e0\u00e1\u00e2\u00e3\u00e4\u00e5\u00e6\u00e7\u00e8\u00e9\u00ea\u00eb\u00ec\u00ed\u00ee\u00ef\u00f0\u00f1\u00f2\u00f3\u00f4\u00f5\u00f6\u00f8\u00f9\u00fa\u00fb\u00fc\u00fd\u00fe\u00ff\u0101\u0103\u0105\u0107\u0109\u010b\u010d\u010f\u0111\u0113\u0115\u0117\u0119\u011b\u011d\u011f\u0121\u0123\u0125\u0127\u0129\u012b\u012d\u012f\u0131\u0133\u0135\u0137\u0138\u013a\u013c\u013e\u0140\u0142\u0144\u0146\u0148\u0149\u014b\u014d\u014f\u0151\u0153\u0155\u0157\u0159\u015b\u015d\u015f\u0161\u0163\u0165\u0167\u0169\u016b\u016d\u016f\u0171\u0173\u0175\u0177\u017a\u017c\u017e\u017f\u0180\u0183\u0185\u0188\u018c\u018d\u0192\u0195\u0199\u019a\u019b\u019e\u01a1\u01a3\u01a5\u01a8\u01aa\u01ab\u01ad\u01b0\u01b4\u01b6\u01b9\u01ba\u01bd\u01be\u01bf\u01c6\u01c9\u01cc\u01ce\u01d0\u01d2\u01d4\u01d6\u01d8\u01da\u01dc\u01dd\u01df\u01e1\u01e3\u01e5\u01e7\u01e9\u01eb\u01ed\u01ef\u01f0\u01f3\u01f5\u01f9\u01fb\u01fd\u01ff\u0201\u0203\u0205\u0207\u0209\u020b\u020d\u020f\u0211\u0213\u0215\u0217\u0219\u021b\u021d\u021f\u0223\u0225\u0227\u0229\u022b\u022d\u022f\u0231\u0233\u0250\u0251\u0252\u0253\u0254\u0255\u0256\u0257\u0258\u0259\u025a\u025b\u025c\u025d\u025e\u025f\u0260\u0261\u0262\u0263\u0264\u0265\u0266\u0267\u0268\u0269\u026a\u026b\u026c\u026d\u026e\u026f\u0270\u0271\u0272\u0273\u0274\u0275\u0276\u0277\u0278\u0279\u027a\u027b\u027c\u027d\u027e\u027f\u0280\u0281\u0282\u0283\u0284\u0285\u0286\u0287\u0288\u0289\u028a\u028b\u028c\u028d\u028e\u028f\u0290\u0291\u0292\u0293\u0294\u0295\u0296\u0297\u0298\u0299\u029a\u029b\u029c\u029d\u029e\u029f\u02a0\u02a1\u02a2\u02a3\u02a4\u02a5\u02a6\u02a7\u02a8\u02a9\u02aa\u02ab\u02ac\u02ad\u0390\u03ac\u03ad\u03ae\u03af\u03b0\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03bf\u03c0\u03c1\u03c2\u03c3\u03c4\u03c5\u03c6\u03c7\u03c8\u03c9\u03ca\u03cb\u03cc\u03cd\u03ce\u03d0\u03d1\u03d5\u03d6\u03d7\u03d9\u03db\u03dd\u03df\u03e1\u03e3\u03e5\u03e7\u03e9\u03eb\u03ed\u03ef\u03f0\u03f1\u03f2\u03f3\u03f5\u0430\u0431\u0432\u0433\u0434\u0435\u0436\u0437\u0438\u0439\u043a\u043b\u043c\u043d\u043e\u043f\u0440\u0441\u0442\u0443\u0444\u0445\u0446\u0447\u0448\u0449\u044a\u044b\u044c\u044d\u044e\u044f\u0450\u0451\u0452\u0453\u0454\u0455\u0456\u0457\u0458\u0459\u045a\u045b\u045c\u045d\u045e\u045f\u0461\u0463\u0465\u0467\u0469\u046b\u046d\u046f\u0471\u0473\u0475\u0477\u0479\u047b\u047d\u047f\u0481\u048b\u048d\u048f\u0491\u0493\u0495\u0497\u0499\u049b\u049d\u049f\u04a1\u04a3\u04a5\u04a7\u04a9\u04ab\u04ad\u04af\u04b1\u04b3\u04b5\u04b7\u04b9\u04bb\u04bd\u04bf\u04c2\u04c4\u04c6\u04c8\u04ca\u04cc\u04ce\u04d1\u04d3\u04d5\u04d7\u04d9\u04db\u04dd\u04df\u04e1\u04e3\u04e5\u04e7\u04e9\u04eb\u04ed\u04ef\u04f1\u04f3\u04f5\u04f9\u0501\u0503\u0505\u0507\u0509\u050b\u050d\u050f\u0561\u0562\u0563\u0564\u0565\u0566\u0567\u0568\u0569\u056a\u056b\u056c\u056d\u056e\u056f\u0570\u0571\u0572\u0573\u0574\u0575\u0576\u0577\u0578\u0579\u057a\u057b\u057c\u057d\u057e\u057f\u0580\u0581\u0582\u0583\u0584\u0585\u0586\u0587\u1e01\u1e03\u1e05\u1e07\u1e09\u1e0b\u1e0d\u1e0f\u1e11\u1e13\u1e15\u1e17\u1e19\u1e1b\u1e1d\u1e1f\u1e21\u1e23\u1e25\u1e27\u1e29\u1e2b\u1e2d\u1e2f\u1e31\u1e33\u1e35\u1e37\u1e39\u1e3b\u1e3d\u1e3f\u1e41\u1e43\u1e45\u1e47\u1e49\u1e4b\u1e4d\u1e4f\u1e51\u1e53\u1e55\u1e57\u1e59\u1e5b\u1e5d\u1e5f\u1e61\u1e63\u1e65\u1e67\u1e69\u1e6b\u1e6d\u1e6f\u1e71\u1e73\u1e75\u1e77\u1e79\u1e7b\u1e7d\u1e7f\u1e81\u1e83\u1e85\u1e87\u1e89\u1e8b\u1e8d\u1e8f\u1e91\u1e93\u1e95\u1e96\u1e97\u1e98\u1e99\u1e9a\u1e9b\u1ea1\u1ea3\u1ea5\u1ea7\u1ea9\u1eab\u1ead\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u1eb9\u1ebb\u1ebd\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u1ec9\u1ecb\u1ecd\u1ecf\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9\u1edb\u1edd\u1edf\u1ee1\u1ee3\u1ee5\u1ee7\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u1ef3\u1ef5\u1ef7\u1ef9\u1f00\u1f01\u1f02\u1f03\u1f04\u1f05\u1f06\u1f07\u1f10\u1f11\u1f12\u1f13\u1f14\u1f15\u1f20\u1f21\u1f22\u1f23\u1f24\u1f25\u1f26\u1f27\u1f30\u1f31\u1f32\u1f33\u1f34\u1f35\u1f36\u1f37\u1f40\u1f41\u1f42\u1f43\u1f44\u1f45\u1f50\u1f51\u1f52\u1f53\u1f54\u1f55\u1f56\u1f57\u1f60\u1f61\u1f62\u1f63\u1f64\u1f65\u1f66\u1f67\u1f70\u1f71\u1f72\u1f73\u1f74\u1f75\u1f76\u1f77\u1f78\u1f79\u1f7a\u1f7b\u1f7c\u1f7d\u1f80\u1f81\u1f82\u1f83\u1f84\u1f85\u1f86\u1f87\u1f90\u1f91\u1f92\u1f93\u1f94\u1f95\u1f96\u1f97\u1fa0\u1fa1\u1fa2\u1fa3\u1fa4\u1fa5\u1fa6\u1fa7\u1fb0\u1fb1\u1fb2\u1fb3\u1fb4\u1fb6\u1fb7\u1fbe\u1fc2\u1fc3\u1fc4\u1fc6\u1fc7\u1fd0\u1fd1\u1fd2\u1fd3\u1fd6\u1fd7\u1fe0\u1fe1\u1fe2\u1fe3\u1fe4\u1fe5\u1fe6\u1fe7\u1ff2\u1ff3\u1ff4\u1ff6\u1ff7\u2071\u207f\u210a\u210e\u210f\u2113\u212f\u2134\u2139\u213d\u2146\u2147\u2148\u2149\ufb00\ufb01\ufb02\ufb03\ufb04\ufb05\ufb06\ufb13\ufb14\ufb15\ufb16\ufb17\uff41\uff42\uff43\uff44\uff45\uff46\uff47\uff48\uff49\uff4a\uff4b\uff4c\uff4d\uff4e\uff4f\uff50\uff51\uff52\uff53\uff54\uff55\uff56\uff57\uff58\uff59\uff5a\u0030\u0031\u0032\u0033\u0034\u0035\u0036\u0037\u0038\u0039\u00b2\u00b3\u00b9\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f\u09e6\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee\u09ef\u0a66\u0a67\u0a68\u0a69\u0a6a\u0a6b\u0a6c\u0a6d\u0a6e\u0a6f\u0ae6\u0ae7\u0ae8\u0ae9\u0aea\u0aeb\u0aec\u0aed\u0aee\u0aef\u0b66\u0b67\u0b68\u0b69\u0b6a\u0b6b\u0b6c\u0b6d\u0b6e\u0b6f\u0be7\u0be8\u0be9\u0bea\u0beb\u0bec\u0bed\u0bee\u0bef\u0c66\u0c67\u0c68\u0c69\u0c6a\u0c6b\u0c6c\u0c6d\u0c6e\u0c6f\u0ce6\u0ce7\u0ce8\u0ce9\u0cea\u0ceb\u0cec\u0ced\u0cee\u0cef\u0d66\u0d67\u0d68\u0d69\u0d6a\u0d6b\u0d6c\u0d6d\u0d6e\u0d6f\u0e50\u0e51\u0e52\u0e53\u0e54\u0e55\u0e56\u0e57\u0e58\u0e59\u0ed0\u0ed1\u0ed2\u0ed3\u0ed4\u0ed5\u0ed6\u0ed7\u0ed8\u0ed9\u0f20\u0f21\u0f22\u0f23\u0f24\u0f25\u0f26\u0f27\u0f28\u0f29\u1040\u1041\u1042\u1043\u1044\u1045\u1046\u1047\u1048\u1049\u1369\u136a\u136b\u136c\u136d\u136e\u136f\u1370\u1371\u17e0\u17e1\u17e2\u17e3\u17e4\u17e5\u17e6\u17e7\u17e8\u17e9\u1810\u1811\u1812\u1813\u1814\u1815\u1816\u1817\u1818\u1819\u2070\u2074\u2075\u2076\u2077\u2078\u2079\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2474\u2475\u2476\u2477\u2478\u2479\u247a\u247b\u247c\u2488\u2489\u248a\u248b\u248c\u248d\u248e\u248f\u2490\u24ea\u24f5\u24f6\u24f7\u24f8\u24f9\u24fa\u24fb\u24fc\u24fd\u2776\u2777\u2778\u2779\u277a\u277b\u277c\u277d\u277e\u2780\u2781\u2782\u2783\u2784\u2785\u2786\u2787\u2788\u278a\u278b\u278c\u278d\u278e\u278f\u2790\u2791\u2792\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19"
chars_digits = u"\u0030\u0031\u0032\u0033\u0034\u0035\u0036\u0037\u0038\u0039\u00b2\u00b3\u00b9\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u0966\u0967\u0968\u0969\u096a\u096b\u096c\u096d\u096e\u096f\u09e6\u09e7\u09e8\u09e9\u09ea\u09eb\u09ec\u09ed\u09ee\u09ef\u0a66\u0a67\u0a68\u0a69\u0a6a\u0a6b\u0a6c\u0a6d\u0a6e\u0a6f\u0ae6\u0ae7\u0ae8\u0ae9\u0aea\u0aeb\u0aec\u0aed\u0aee\u0aef\u0b66\u0b67\u0b68\u0b69\u0b6a\u0b6b\u0b6c\u0b6d\u0b6e\u0b6f\u0be7\u0be8\u0be9\u0bea\u0beb\u0bec\u0bed\u0bee\u0bef\u0c66\u0c67\u0c68\u0c69\u0c6a\u0c6b\u0c6c\u0c6d\u0c6e\u0c6f\u0ce6\u0ce7\u0ce8\u0ce9\u0cea\u0ceb\u0cec\u0ced\u0cee\u0cef\u0d66\u0d67\u0d68\u0d69\u0d6a\u0d6b\u0d6c\u0d6d\u0d6e\u0d6f\u0e50\u0e51\u0e52\u0e53\u0e54\u0e55\u0e56\u0e57\u0e58\u0e59\u0ed0\u0ed1\u0ed2\u0ed3\u0ed4\u0ed5\u0ed6\u0ed7\u0ed8\u0ed9\u0f20\u0f21\u0f22\u0f23\u0f24\u0f25\u0f26\u0f27\u0f28\u0f29\u1040\u1041\u1042\u1043\u1044\u1045\u1046\u1047\u1048\u1049\u1369\u136a\u136b\u136c\u136d\u136e\u136f\u1370\u1371\u17e0\u17e1\u17e2\u17e3\u17e4\u17e5\u17e6\u17e7\u17e8\u17e9\u1810\u1811\u1812\u1813\u1814\u1815\u1816\u1817\u1818\u1819\u2070\u2074\u2075\u2076\u2077\u2078\u2079\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2474\u2475\u2476\u2477\u2478\u2479\u247a\u247b\u247c\u2488\u2489\u248a\u248b\u248c\u248d\u248e\u248f\u2490\u24ea\u24f5\u24f6\u24f7\u24f8\u24f9\u24fa\u24fb\u24fc\u24fd\u2776\u2777\u2778\u2779\u277a\u277b\u277c\u277d\u277e\u2780\u2781\u2782\u2783\u2784\u2785\u2786\u2787\u2788\u278a\u278b\u278c\u278d\u278e\u278f\u2790\u2791\u2792\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19"
chars_spaces = u"\u0009\u000a\u000b\u000c\u000d\u001c\u001d\u001e\u001f\u0020\u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u200b\u2028\u2029\u202f\u205f\u3000"

punct_pattern = re.escape(u'''"\'}]|:,.)?!''')

# from MoinMoin.parser.text_moin_wiki import Parser as WikiParser
interwiki_rule = ur'''
    (?:^|(?<=\W))  # require either beginning of line or some non-alphanum char (whitespace, punctuation) to the left
    (?P<interwiki_wiki>[A-Z][a-zA-Z]+)  # interwiki wiki name
    \:
    (?P<interwiki_page>  # interwiki page name
     (?=[^ ]*[%(u)s%(l)s0..9][^ ]*\ )  # make sure there is something non-blank with at least one alphanum letter following
     [^\s%(punct)s]+  # we take all until we hit some blank or punctuation char ...
    )
''' % {
    'u': chars_upper,
    'l': chars_lower,
    'punct': punct_pattern,
}

interwiki_re = re.compile(interwiki_rule, re.VERBOSE|re.UNICODE)

# Portions (C) International Organization for Standardization 1986
# Permission to copy in any form is granted for use with
# conforming SGML systems and applications as defined in
# ISO 8879, provided this notice is included in all copies.
dtd = ur'''
<!DOCTYPE html [
<!ENTITY nbsp   "&#32;">  <!-- no-break space = non-breaking space, U+00A0, convert to U+0020 -->
<!ENTITY iexcl  "&#161;"> <!-- inverted exclamation mark, U+00A1 ISOnum -->
<!ENTITY cent   "&#162;"> <!-- cent sign, U+00A2 ISOnum -->
<!ENTITY pound  "&#163;"> <!-- pound sign, U+00A3 ISOnum -->
<!ENTITY curren "&#164;"> <!-- currency sign, U+00A4 ISOnum -->
<!ENTITY yen    "&#165;"> <!-- yen sign = yuan sign, U+00A5 ISOnum -->
<!ENTITY brvbar "&#166;"> <!-- broken bar = broken vertical bar, U+00A6 ISOnum -->
<!ENTITY sect   "&#167;"> <!-- section sign, U+00A7 ISOnum -->
<!ENTITY uml    "&#168;"> <!-- diaeresis = spacing diaeresis, U+00A8 ISOdia -->
<!ENTITY copy   "&#169;"> <!-- copyright sign, U+00A9 ISOnum -->
<!ENTITY ordf   "&#170;"> <!-- feminine ordinal indicator, U+00AA ISOnum -->
<!ENTITY laquo  "&#171;"> <!-- left-pointing double angle quotation mark = left pointing guillemet, U+00AB ISOnum -->
<!ENTITY not    "&#172;"> <!-- not sign = angled dash, U+00AC ISOnum -->
<!ENTITY shy    "&#173;"> <!-- soft hyphen = discretionary hyphen, U+00AD ISOnum -->
<!ENTITY reg    "&#174;"> <!-- registered sign = registered trade mark sign, U+00AE ISOnum -->
<!ENTITY macr   "&#175;"> <!-- macron = spacing macron = overline = APL overbar, U+00AF ISOdia -->
<!ENTITY deg    "&#176;"> <!-- degree sign, U+00B0 ISOnum -->
<!ENTITY plusmn "&#177;"> <!-- plus-minus sign = plus-or-minus sign, U+00B1 ISOnum -->
<!ENTITY sup2   "&#178;"> <!-- superscript two = superscript digit two = squared, U+00B2 ISOnum -->
<!ENTITY sup3   "&#179;"> <!-- superscript three = superscript digit three = cubed, U+00B3 ISOnum -->
<!ENTITY acute  "&#180;"> <!-- acute accent = spacing acute, U+00B4 ISOdia -->
<!ENTITY micro  "&#181;"> <!-- micro sign, U+00B5 ISOnum -->
<!ENTITY para   "&#182;"> <!-- pilcrow sign = paragraph sign, U+00B6 ISOnum -->
<!ENTITY middot "&#183;"> <!-- middle dot = Georgian comma = Greek middle dot, U+00B7 ISOnum -->
<!ENTITY cedil  "&#184;"> <!-- cedilla = spacing cedilla, U+00B8 ISOdia -->
<!ENTITY sup1   "&#185;"> <!-- superscript one = superscript digit one, U+00B9 ISOnum -->
<!ENTITY ordm   "&#186;"> <!-- masculine ordinal indicator, U+00BA ISOnum -->
<!ENTITY raquo  "&#187;"> <!-- right-pointing double angle quotation mark = right pointing guillemet, U+00BB ISOnum -->
<!ENTITY frac14 "&#188;"> <!-- vulgar fraction one quarter = fraction one quarter, U+00BC ISOnum -->
<!ENTITY frac12 "&#189;"> <!-- vulgar fraction one half = fraction one half, U+00BD ISOnum -->
<!ENTITY frac34 "&#190;"> <!-- vulgar fraction three quarters = fraction three quarters, U+00BE ISOnum -->
<!ENTITY iquest "&#191;"> <!-- inverted question mark = turned question mark, U+00BF ISOnum -->
<!ENTITY Agrave "&#192;"> <!-- latin capital letter A with grave = latin capital letter A grave, U+00C0 ISOlat1 -->
<!ENTITY Aacute "&#193;"> <!-- latin capital letter A with acute, U+00C1 ISOlat1 -->
<!ENTITY Acirc  "&#194;"> <!-- latin capital letter A with circumflex, U+00C2 ISOlat1 -->
<!ENTITY Atilde "&#195;"> <!-- latin capital letter A with tilde, U+00C3 ISOlat1 -->
<!ENTITY Auml   "&#196;"> <!-- latin capital letter A with diaeresis, U+00C4 ISOlat1 -->
<!ENTITY Aring  "&#197;"> <!-- latin capital letter A with ring above = latin capital letter A ring, U+00C5 ISOlat1 -->
<!ENTITY AElig  "&#198;"> <!-- latin capital letter AE = latin capital ligature AE, U+00C6 ISOlat1 -->
<!ENTITY Ccedil "&#199;"> <!-- latin capital letter C with cedilla, U+00C7 ISOlat1 -->
<!ENTITY Egrave "&#200;"> <!-- latin capital letter E with grave, U+00C8 ISOlat1 -->
<!ENTITY Eacute "&#201;"> <!-- latin capital letter E with acute, U+00C9 ISOlat1 -->
<!ENTITY Ecirc  "&#202;"> <!-- latin capital letter E with circumflex, U+00CA ISOlat1 -->
<!ENTITY Euml   "&#203;"> <!-- latin capital letter E with diaeresis, U+00CB ISOlat1 -->
<!ENTITY Igrave "&#204;"> <!-- latin capital letter I with grave, U+00CC ISOlat1 -->
<!ENTITY Iacute "&#205;"> <!-- latin capital letter I with acute, U+00CD ISOlat1 -->
<!ENTITY Icirc  "&#206;"> <!-- latin capital letter I with circumflex, U+00CE ISOlat1 -->
<!ENTITY Iuml   "&#207;"> <!-- latin capital letter I with diaeresis, U+00CF ISOlat1 -->
<!ENTITY ETH    "&#208;"> <!-- latin capital letter ETH, U+00D0 ISOlat1 -->
<!ENTITY Ntilde "&#209;"> <!-- latin capital letter N with tilde, U+00D1 ISOlat1 -->
<!ENTITY Ograve "&#210;"> <!-- latin capital letter O with grave, U+00D2 ISOlat1 -->
<!ENTITY Oacute "&#211;"> <!-- latin capital letter O with acute, U+00D3 ISOlat1 -->
<!ENTITY Ocirc  "&#212;"> <!-- latin capital letter O with circumflex, U+00D4 ISOlat1 -->
<!ENTITY Otilde "&#213;"> <!-- latin capital letter O with tilde, U+00D5 ISOlat1 -->
<!ENTITY Ouml   "&#214;"> <!-- latin capital letter O with diaeresis, U+00D6 ISOlat1 -->
<!ENTITY times  "&#215;"> <!-- multiplication sign, U+00D7 ISOnum -->
<!ENTITY Oslash "&#216;"> <!-- latin capital letter O with stroke = latin capital letter O slash, U+00D8 ISOlat1 -->
<!ENTITY Ugrave "&#217;"> <!-- latin capital letter U with grave, U+00D9 ISOlat1 -->
<!ENTITY Uacute "&#218;"> <!-- latin capital letter U with acute, U+00DA ISOlat1 -->
<!ENTITY Ucirc  "&#219;"> <!-- latin capital letter U with circumflex, U+00DB ISOlat1 -->
<!ENTITY Uuml   "&#220;"> <!-- latin capital letter U with diaeresis, U+00DC ISOlat1 -->
<!ENTITY Yacute "&#221;"> <!-- latin capital letter Y with acute, U+00DD ISOlat1 -->
<!ENTITY THORN  "&#222;"> <!-- latin capital letter THORN, U+00DE ISOlat1 -->
<!ENTITY szlig  "&#223;"> <!-- latin small letter sharp s = ess-zed, U+00DF ISOlat1 -->
<!ENTITY agrave "&#224;"> <!-- latin small letter a with grave = latin small letter a grave, U+00E0 ISOlat1 -->
<!ENTITY aacute "&#225;"> <!-- latin small letter a with acute, U+00E1 ISOlat1 -->
<!ENTITY acirc  "&#226;"> <!-- latin small letter a with circumflex, U+00E2 ISOlat1 -->
<!ENTITY atilde "&#227;"> <!-- latin small letter a with tilde, U+00E3 ISOlat1 -->
<!ENTITY auml   "&#228;"> <!-- latin small letter a with diaeresis, U+00E4 ISOlat1 -->
<!ENTITY aring  "&#229;"> <!-- latin small letter a with ring above = latin small letter a ring, U+00E5 ISOlat1 -->
<!ENTITY aelig  "&#230;"> <!-- latin small letter ae = latin small ligature ae, U+00E6 ISOlat1 -->
<!ENTITY ccedil "&#231;"> <!-- latin small letter c with cedilla, U+00E7 ISOlat1 -->
<!ENTITY egrave "&#232;"> <!-- latin small letter e with grave, U+00E8 ISOlat1 -->
<!ENTITY eacute "&#233;"> <!-- latin small letter e with acute, U+00E9 ISOlat1 -->
<!ENTITY ecirc  "&#234;"> <!-- latin small letter e with circumflex, U+00EA ISOlat1 -->
<!ENTITY euml   "&#235;"> <!-- latin small letter e with diaeresis, U+00EB ISOlat1 -->
<!ENTITY igrave "&#236;"> <!-- latin small letter i with grave, U+00EC ISOlat1 -->
<!ENTITY iacute "&#237;"> <!-- latin small letter i with acute, U+00ED ISOlat1 -->
<!ENTITY icirc  "&#238;"> <!-- latin small letter i with circumflex, U+00EE ISOlat1 -->
<!ENTITY iuml   "&#239;"> <!-- latin small letter i with diaeresis, U+00EF ISOlat1 -->
<!ENTITY eth    "&#240;"> <!-- latin small letter eth, U+00F0 ISOlat1 -->
<!ENTITY ntilde "&#241;"> <!-- latin small letter n with tilde, U+00F1 ISOlat1 -->
<!ENTITY ograve "&#242;"> <!-- latin small letter o with grave, U+00F2 ISOlat1 -->
<!ENTITY oacute "&#243;"> <!-- latin small letter o with acute, U+00F3 ISOlat1 -->
<!ENTITY ocirc  "&#244;"> <!-- latin small letter o with circumflex, U+00F4 ISOlat1 -->
<!ENTITY otilde "&#245;"> <!-- latin small letter o with tilde, U+00F5 ISOlat1 -->
<!ENTITY ouml   "&#246;"> <!-- latin small letter o with diaeresis, U+00F6 ISOlat1 -->
<!ENTITY divide "&#247;"> <!-- division sign, U+00F7 ISOnum -->
<!ENTITY oslash "&#248;"> <!-- latin small letter o with stroke, = latin small letter o slash, U+00F8 ISOlat1 -->
<!ENTITY ugrave "&#249;"> <!-- latin small letter u with grave, U+00F9 ISOlat1 -->
<!ENTITY uacute "&#250;"> <!-- latin small letter u with acute, U+00FA ISOlat1 -->
<!ENTITY ucirc  "&#251;"> <!-- latin small letter u with circumflex, U+00FB ISOlat1 -->
<!ENTITY uuml   "&#252;"> <!-- latin small letter u with diaeresis, U+00FC ISOlat1 -->
<!ENTITY yacute "&#253;"> <!-- latin small letter y with acute, U+00FD ISOlat1 -->
<!ENTITY thorn  "&#254;"> <!-- latin small letter thorn, U+00FE ISOlat1 -->
<!ENTITY yuml   "&#255;"> <!-- latin small letter y with diaeresis, U+00FF ISOlat1 -->

<!-- Latin Extended-B -->
<!ENTITY fnof     "&#402;"> <!-- latin small f with hook = function                                    = florin, U+0192 ISOtech -->

<!-- Greek -->
<!ENTITY Alpha    "&#913;"> <!-- greek capital letter alpha, U+0391 -->
<!ENTITY Beta     "&#914;"> <!-- greek capital letter beta, U+0392 -->
<!ENTITY Gamma    "&#915;"> <!-- greek capital letter gamma,
                                    U+0393 ISOgrk3 -->
<!ENTITY Delta    "&#916;"> <!-- greek capital letter delta,
                                    U+0394 ISOgrk3 -->
<!ENTITY Epsilon  "&#917;"> <!-- greek capital letter epsilon, U+0395 -->
<!ENTITY Zeta     "&#918;"> <!-- greek capital letter zeta, U+0396 -->
<!ENTITY Eta      "&#919;"> <!-- greek capital letter eta, U+0397 -->
<!ENTITY Theta    "&#920;"> <!-- greek capital letter theta,
                                    U+0398 ISOgrk3 -->
<!ENTITY Iota     "&#921;"> <!-- greek capital letter iota, U+0399 -->
<!ENTITY Kappa    "&#922;"> <!-- greek capital letter kappa, U+039A -->
<!ENTITY Lambda   "&#923;"> <!-- greek capital letter lambda,
                                    U+039B ISOgrk3 -->
<!ENTITY Mu       "&#924;"> <!-- greek capital letter mu, U+039C -->
<!ENTITY Nu       "&#925;"> <!-- greek capital letter nu, U+039D -->
<!ENTITY Xi       "&#926;"> <!-- greek capital letter xi, U+039E ISOgrk3 -->
<!ENTITY Omicron  "&#927;"> <!-- greek capital letter omicron, U+039F -->
<!ENTITY Pi       "&#928;"> <!-- greek capital letter pi, U+03A0 ISOgrk3 -->
<!ENTITY Rho      "&#929;"> <!-- greek capital letter rho, U+03A1 -->
<!-- there is no Sigmaf, and no U+03A2 character either -->
<!ENTITY Sigma    "&#931;"> <!-- greek capital letter sigma,
                                    U+03A3 ISOgrk3 -->
<!ENTITY Tau      "&#932;"> <!-- greek capital letter tau, U+03A4 -->
<!ENTITY Upsilon  "&#933;"> <!-- greek capital letter upsilon,
                                    U+03A5 ISOgrk3 -->
<!ENTITY Phi      "&#934;"> <!-- greek capital letter phi,
                                    U+03A6 ISOgrk3 -->
<!ENTITY Chi      "&#935;"> <!-- greek capital letter chi, U+03A7 -->
<!ENTITY Psi      "&#936;"> <!-- greek capital letter psi,
                                    U+03A8 ISOgrk3 -->
<!ENTITY Omega    "&#937;"> <!-- greek capital letter omega,
                                    U+03A9 ISOgrk3 -->

<!ENTITY alpha    "&#945;"> <!-- greek small letter alpha,
                                    U+03B1 ISOgrk3 -->
<!ENTITY beta     "&#946;"> <!-- greek small letter beta, U+03B2 ISOgrk3 -->
<!ENTITY gamma    "&#947;"> <!-- greek small letter gamma,
                                    U+03B3 ISOgrk3 -->
<!ENTITY delta    "&#948;"> <!-- greek small letter delta,
                                    U+03B4 ISOgrk3 -->
<!ENTITY epsilon  "&#949;"> <!-- greek small letter epsilon,
                                    U+03B5 ISOgrk3 -->
<!ENTITY zeta     "&#950;"> <!-- greek small letter zeta, U+03B6 ISOgrk3 -->
<!ENTITY eta      "&#951;"> <!-- greek small letter eta, U+03B7 ISOgrk3 -->
<!ENTITY theta    "&#952;"> <!-- greek small letter theta,
                                    U+03B8 ISOgrk3 -->
<!ENTITY iota     "&#953;"> <!-- greek small letter iota, U+03B9 ISOgrk3 -->
<!ENTITY kappa    "&#954;"> <!-- greek small letter kappa,
                                    U+03BA ISOgrk3 -->
<!ENTITY lambda   "&#955;"> <!-- greek small letter lambda,
                                    U+03BB ISOgrk3 -->
<!ENTITY mu       "&#956;"> <!-- greek small letter mu, U+03BC ISOgrk3 -->
<!ENTITY nu       "&#957;"> <!-- greek small letter nu, U+03BD ISOgrk3 -->
<!ENTITY xi       "&#958;"> <!-- greek small letter xi, U+03BE ISOgrk3 -->
<!ENTITY omicron  "&#959;"> <!-- greek small letter omicron, U+03BF NEW -->
<!ENTITY pi       "&#960;"> <!-- greek small letter pi, U+03C0 ISOgrk3 -->
<!ENTITY rho      "&#961;"> <!-- greek small letter rho, U+03C1 ISOgrk3 -->
<!ENTITY sigmaf   "&#962;"> <!-- greek small letter final sigma,
                                    U+03C2 ISOgrk3 -->
<!ENTITY sigma    "&#963;"> <!-- greek small letter sigma,
                                    U+03C3 ISOgrk3 -->
<!ENTITY tau      "&#964;"> <!-- greek small letter tau, U+03C4 ISOgrk3 -->
<!ENTITY upsilon  "&#965;"> <!-- greek small letter upsilon,
                                    U+03C5 ISOgrk3 -->
<!ENTITY phi      "&#966;"> <!-- greek small letter phi, U+03C6 ISOgrk3 -->
<!ENTITY chi      "&#967;"> <!-- greek small letter chi, U+03C7 ISOgrk3 -->
<!ENTITY psi      "&#968;"> <!-- greek small letter psi, U+03C8 ISOgrk3 -->
<!ENTITY omega    "&#969;"> <!-- greek small letter omega,
                                    U+03C9 ISOgrk3 -->
<!ENTITY thetasym "&#977;"> <!-- greek small letter theta symbol,
                                    U+03D1 NEW -->
<!ENTITY upsih    "&#978;"> <!-- greek upsilon with hook symbol,
                                    U+03D2 NEW -->
<!ENTITY piv      "&#982;"> <!-- greek pi symbol, U+03D6 ISOgrk3 -->

<!-- General Punctuation -->
<!ENTITY bull     "&#8226;"> <!-- bullet = black small circle,
                                     U+2022 ISOpub  -->
<!-- bullet is NOT the same as bullet operator, U+2219 -->
<!ENTITY hellip   "&#8230;"> <!-- horizontal ellipsis = three dot leader,
                                     U+2026 ISOpub  -->
<!ENTITY prime    "&#8242;"> <!-- prime = minutes = feet, U+2032 ISOtech -->
<!ENTITY Prime    "&#8243;"> <!-- double prime = seconds = inches,
                                     U+2033 ISOtech -->
<!ENTITY oline    "&#8254;"> <!-- overline = spacing overscore,
                                     U+203E NEW -->
<!ENTITY frasl    "&#8260;"> <!-- fraction slash, U+2044 NEW -->

<!-- Letterlike Symbols -->
<!ENTITY weierp   "&#8472;"> <!-- script capital P = power set
                                     = Weierstrass p, U+2118 ISOamso -->
<!ENTITY image    "&#8465;"> <!-- blackletter capital I = imaginary part,
                                     U+2111 ISOamso -->
<!ENTITY real     "&#8476;"> <!-- blackletter capital R = real part symbol,
                                     U+211C ISOamso -->
<!ENTITY trade    "&#8482;"> <!-- trade mark sign, U+2122 ISOnum -->
<!ENTITY alefsym  "&#8501;"> <!-- alef symbol = first transfinite cardinal,
                                     U+2135 NEW -->
<!-- alef symbol is NOT the same as hebrew letter alef,
     U+05D0 although the same glyph could be used to depict both characters -->

<!-- Arrows -->
<!ENTITY larr     "&#8592;"> <!-- leftwards arrow, U+2190 ISOnum -->
<!ENTITY uarr     "&#8593;"> <!-- upwards arrow, U+2191 ISOnum-->
<!ENTITY rarr     "&#8594;"> <!-- rightwards arrow, U+2192 ISOnum -->
<!ENTITY darr     "&#8595;"> <!-- downwards arrow, U+2193 ISOnum -->
<!ENTITY harr     "&#8596;"> <!-- left right arrow, U+2194 ISOamsa -->
<!ENTITY crarr    "&#8629;"> <!-- downwards arrow with corner leftwards
                                     = carriage return, U+21B5 NEW -->
<!ENTITY lArr     "&#8656;"> <!-- leftwards double arrow, U+21D0 ISOtech -->
<!-- ISO 10646 does not say that lArr is the same as the 'is implied by' arrow
    but also does not have any other character for that function. So ? lArr can
    be used for 'is implied by' as ISOtech suggests -->
<!ENTITY uArr     "&#8657;"> <!-- upwards double arrow, U+21D1 ISOamsa -->
<!ENTITY rArr     "&#8658;"> <!-- rightwards double arrow,
                                     U+21D2 ISOtech -->
<!-- ISO 10646 does not say this is the 'implies' character but does not have
     another character with this function so ?
     rArr can be used for 'implies' as ISOtech suggests -->
<!ENTITY dArr     "&#8659;"> <!-- downwards double arrow, U+21D3 ISOamsa -->
<!ENTITY hArr     "&#8660;"> <!-- left right double arrow,
                                     U+21D4 ISOamsa -->

<!-- Mathematical Operators -->
<!ENTITY forall   "&#8704;"> <!-- for all, U+2200 ISOtech -->
<!ENTITY part     "&#8706;"> <!-- partial differential, U+2202 ISOtech  -->
<!ENTITY exist    "&#8707;"> <!-- there exists, U+2203 ISOtech -->
<!ENTITY empty    "&#8709;"> <!-- empty set = null set = diameter,
                                     U+2205 ISOamso -->
<!ENTITY nabla    "&#8711;"> <!-- nabla = backward difference,
                                     U+2207 ISOtech -->
<!ENTITY isin     "&#8712;"> <!-- element of, U+2208 ISOtech -->
<!ENTITY notin    "&#8713;"> <!-- not an element of, U+2209 ISOtech -->
<!ENTITY ni       "&#8715;"> <!-- contains as member, U+220B ISOtech -->
<!-- should there be a more memorable name than 'ni'? -->
<!ENTITY prod     "&#8719;"> <!-- n-ary product = product sign,
                                     U+220F ISOamsb -->
<!-- prod is NOT the same character as U+03A0 'greek capital letter pi' though
     the same glyph might be used for both -->
<!ENTITY sum      "&#8721;"> <!-- n-ary sumation, U+2211 ISOamsb -->
<!-- sum is NOT the same character as U+03A3 'greek capital letter sigma'
     though the same glyph might be used for both -->
<!ENTITY minus    "&#8722;"> <!-- minus sign, U+2212 ISOtech -->
<!ENTITY lowast   "&#8727;"> <!-- asterisk operator, U+2217 ISOtech -->
<!ENTITY radic    "&#8730;"> <!-- square root = radical sign,
                                     U+221A ISOtech -->
<!ENTITY prop     "&#8733;"> <!-- proportional to, U+221D ISOtech -->
<!ENTITY infin    "&#8734;"> <!-- infinity, U+221E ISOtech -->
<!ENTITY ang      "&#8736;"> <!-- angle, U+2220 ISOamso -->
<!ENTITY and      "&#8743;"> <!-- logical and = wedge, U+2227 ISOtech -->
<!ENTITY or       "&#8744;"> <!-- logical or = vee, U+2228 ISOtech -->
<!ENTITY cap      "&#8745;"> <!-- intersection = cap, U+2229 ISOtech -->
<!ENTITY cup      "&#8746;"> <!-- union = cup, U+222A ISOtech -->
<!ENTITY int      "&#8747;"> <!-- integral, U+222B ISOtech -->
<!ENTITY there4   "&#8756;"> <!-- therefore, U+2234 ISOtech -->
<!ENTITY sim      "&#8764;"> <!-- tilde operator = varies with = similar to,
                                     U+223C ISOtech -->
<!-- tilde operator is NOT the same character as the tilde, U+007E,
     although the same glyph might be used to represent both  -->
<!ENTITY cong     "&#8773;"> <!-- approximately equal to, U+2245 ISOtech -->
<!ENTITY asymp    "&#8776;"> <!-- almost equal to = asymptotic to,
                                     U+2248 ISOamsr -->
<!ENTITY ne       "&#8800;"> <!-- not equal to, U+2260 ISOtech -->
<!ENTITY equiv    "&#8801;"> <!-- identical to, U+2261 ISOtech -->
<!ENTITY le       "&#8804;"> <!-- less-than or equal to, U+2264 ISOtech -->
<!ENTITY ge       "&#8805;"> <!-- greater-than or equal to,
                                     U+2265 ISOtech -->
<!ENTITY sub      "&#8834;"> <!-- subset of, U+2282 ISOtech -->
<!ENTITY sup      "&#8835;"> <!-- superset of, U+2283 ISOtech -->
<!-- note that nsup, 'not a superset of, U+2283' is not covered by the Symbol
     font encoding and is not included. Should it be, for symmetry?
     It is in ISOamsn  -->
<!ENTITY nsub     "&#8836;"> <!-- not a subset of, U+2284 ISOamsn -->
<!ENTITY sube     "&#8838;"> <!-- subset of or equal to, U+2286 ISOtech -->
<!ENTITY supe     "&#8839;"> <!-- superset of or equal to,
                                     U+2287 ISOtech -->
<!ENTITY oplus    "&#8853;"> <!-- circled plus = direct sum,
                                     U+2295 ISOamsb -->
<!ENTITY otimes   "&#8855;"> <!-- circled times = vector product,
                                     U+2297 ISOamsb -->
<!ENTITY perp     "&#8869;"> <!-- up tack = orthogonal to = perpendicular,
                                     U+22A5 ISOtech -->
<!ENTITY sdot     "&#8901;"> <!-- dot operator, U+22C5 ISOamsb -->
<!-- dot operator is NOT the same character as U+00B7 middle dot -->

<!-- Miscellaneous Technical -->
<!ENTITY lceil    "&#8968;"> <!-- left ceiling = apl upstile,
                                     U+2308 ISOamsc  -->
<!ENTITY rceil    "&#8969;"> <!-- right ceiling, U+2309 ISOamsc  -->
<!ENTITY lfloor   "&#8970;"> <!-- left floor = apl downstile,
                                     U+230A ISOamsc  -->
<!ENTITY rfloor   "&#8971;"> <!-- right floor, U+230B ISOamsc  -->
<!ENTITY lang     "&#9001;"> <!-- left-pointing angle bracket = bra,
                                     U+2329 ISOtech -->
<!-- lang is NOT the same character as U+003C 'less than'
     or U+2039 'single left-pointing angle quotation mark' -->
<!ENTITY rang     "&#9002;"> <!-- right-pointing angle bracket = ket,
                                     U+232A ISOtech -->
<!-- rang is NOT the same character as U+003E 'greater than'
     or U+203A 'single right-pointing angle quotation mark' -->

<!-- Geometric Shapes -->
<!ENTITY loz      "&#9674;"> <!-- lozenge, U+25CA ISOpub -->

<!-- Miscellaneous Symbols -->
<!ENTITY spades   "&#9824;"> <!-- black spade suit, U+2660 ISOpub -->
<!-- black here seems to mean filled as opposed to hollow -->
<!ENTITY clubs    "&#9827;"> <!-- black club suit = shamrock,
                                     U+2663 ISOpub -->
<!ENTITY hearts   "&#9829;"> <!-- black heart suit = valentine,
                                     U+2665 ISOpub -->
<!ENTITY diams    "&#9830;"> <!-- black diamond suit, U+2666 ISOpub -->

<!-- C0 Controls and Basic Latin -->
<!ENTITY quot    "&#34;"> <!-- quotation mark = APL quote,
                                    U+0022 ISOnum -->
<!ENTITY amp     "&#38;"> <!-- ampersand, U+0026 ISOnum -->
<!ENTITY lt      "&#60;"> <!-- less-than sign, U+003C ISOnum -->
<!ENTITY gt      "&#62;"> <!-- greater-than sign, U+003E ISOnum -->

<!-- Latin Extended-A -->
<!ENTITY OElig   "&#338;"> <!-- latin capital ligature OE,
                                    U+0152 ISOlat2 -->
<!ENTITY oelig   "&#339;"> <!-- latin small ligature oe, U+0153 ISOlat2 -->
<!-- ligature is a misnomer, this is a separate character in some languages -->
<!ENTITY Scaron  "&#352;"> <!-- latin capital letter S with caron,
                                    U+0160 ISOlat2 -->
<!ENTITY scaron  "&#353;"> <!-- latin small letter s with caron,
                                    U+0161 ISOlat2 -->
<!ENTITY Yuml    "&#376;"> <!-- latin capital letter Y with diaeresis,
                                    U+0178 ISOlat2 -->

<!-- Spacing Modifier Letters -->
<!ENTITY circ    "&#710;"> <!-- modifier letter circumflex accent,
                                    U+02C6 ISOpub -->
<!ENTITY tilde   "&#732;"> <!-- small tilde, U+02DC ISOdia -->

<!-- General Punctuation -->
<!ENTITY ensp    "&#8194;"> <!-- en space, U+2002 ISOpub -->
<!ENTITY emsp    "&#8195;"> <!-- em space, U+2003 ISOpub -->
<!ENTITY thinsp  "&#8201;"> <!-- thin space, U+2009 ISOpub -->
<!ENTITY zwnj    "&#8204;"> <!-- zero width non-joiner,
                                    U+200C NEW RFC 2070 -->
<!ENTITY zwj     "&#8205;"> <!-- zero width joiner, U+200D NEW RFC 2070 -->
<!ENTITY lrm     "&#8206;"> <!-- left-to-right mark, U+200E NEW RFC 2070 -->
<!ENTITY rlm     "&#8207;"> <!-- right-to-left mark, U+200F NEW RFC 2070 -->
<!ENTITY ndash   "&#8211;"> <!-- en dash, U+2013 ISOpub -->
<!ENTITY mdash   "&#8212;"> <!-- em dash, U+2014 ISOpub -->
<!ENTITY lsquo   "&#8216;"> <!-- left single quotation mark,
                                    U+2018 ISOnum -->
<!ENTITY rsquo   "&#8217;"> <!-- right single quotation mark,
                                    U+2019 ISOnum -->
<!ENTITY sbquo   "&#8218;"> <!-- single low-9 quotation mark, U+201A NEW -->
<!ENTITY ldquo   "&#8220;"> <!-- left double quotation mark,
                                    U+201C ISOnum -->
<!ENTITY rdquo   "&#8221;"> <!-- right double quotation mark,
                                    U+201D ISOnum -->
<!ENTITY bdquo   "&#8222;"> <!-- double low-9 quotation mark, U+201E NEW -->
<!ENTITY dagger  "&#8224;"> <!-- dagger, U+2020 ISOpub -->
<!ENTITY Dagger  "&#8225;"> <!-- double dagger, U+2021 ISOpub -->
<!ENTITY permil  "&#8240;"> <!-- per mille sign, U+2030 ISOtech -->
<!ENTITY lsaquo  "&#8249;"> <!-- single left-pointing angle quotation mark,
                                    U+2039 ISO proposed -->
<!-- lsaquo is proposed but not yet ISO standardized -->
<!ENTITY rsaquo  "&#8250;"> <!-- single right-pointing angle quotation mark,
                                    U+203A ISO proposed -->
<!-- rsaquo is proposed but not yet ISO standardized -->
<!ENTITY euro   "&#8364;"> <!-- euro sign, U+20AC NEW -->

]>
'''

class visitor(object):
    def do(self, tree):
        self.visit_node_list(tree.childNodes)

    def visit_node_list(self, nodelist):
        for node in nodelist:
            self.visit(node)

    def visit(self, node):
        nodeType = node.nodeType
        if node.nodeType == Node.ELEMENT_NODE:
            return self.visit_element(node)
        elif node.nodeType == Node.ATTRIBUTE_NODE:
            return self.visit_attribute(node)
        elif node.nodeType == Node.TEXT_NODE:
            return self.visit_text(node)
        elif node.nodeType == Node.CDATA_SECTION_NODE:
            return self.visit_cdata_section(node)

    def visit_element(self, node):
        if len(node.childNodes):
            self.visit_node_list(node.childNodes)

    def visit_attribute(self, node):
        pass

    def visit_text(self, node):
        pass

    def visit_cdata_section(self, node):
        pass


class strip_whitespace(visitor):

    def visit_element(self, node):
        if node.localName == 'p':
            # XXX: our formatter adds a whitespace at the end of each paragraph
            if node.hasChildNodes() and node.childNodes[-1].nodeType == Node.TEXT_NODE:
                data = node.childNodes[-1].data.rstrip('\n ')
                # Remove it if empty
                if data == '':
                    node.removeChild(node.childNodes[-1])
                else:
                    node.childNodes[-1].data = data
            # Remove empty paragraphs
            if not node.hasChildNodes():
                node.parentNode.removeChild(node)

        if node.hasChildNodes():
            self.visit_node_list(node.childNodes)


class convert_tree(visitor):
    white_space = object()
    new_line = object()
    new_line_dont_remove = object()

    def __init__(self, pagename, resolve_url):
        self.pagename = pagename
        self.resolve_url = resolve_url

    def do(self, tree):
        self.depth = 0
        self.text = []
        self.visit(tree.documentElement)
        self.check_whitespace()
        return ''.join(self.text)

    def check_whitespace(self):
        i = 0
        text = self.text
        while i < len(text):
            if text[i] is self.white_space:
                if i == 0 or i == len(text)-1:
                    del text[i]
                elif text[i-1].endswith(" ") or text[i-1].endswith("\n"):
                    # last char of previous element is whitespace
                    del text[i]
                elif (text[i+1] is self.white_space or
                      # next element is white_space
                      text[i+1] is self.new_line):
                      # or new_line
                    del text[i]
                elif text[i+1].startswith(" ") or text[i+1].startswith("\n"):
                    # first char of next element is whitespace
                    del text[i]
                else:
                    text[i] = " "
                    i += 1
            elif text[i] is self.new_line:
                if i == 0:
                    del text[i]
                elif i == len(text) - 1:
                    text[i] = "\n"
                    i += 1
                elif text[i-1].endswith("\n") or (
                      isinstance(text[i+1], str) and text[i+1].startswith("\n")):
                    del text[i]
                else:
                    text[i] = "\n"
                    i += 1
            elif text[i] is self.new_line_dont_remove:
                text[i] = "\n"
                i += 1
            else:
                i += 1

    def visit_text(self, node):
        self.text.append(node.data)

    def visit_element(self, node):
        name = node.localName
        if name is None: # not sure this can happen here (DOM comment node), but just for the case
            return
        func = getattr(self, "process_%s" % name, None)
        if func:
            func(node)
        else:
            self.process_inline(node)

    def visit_node_list_element_only(self, nodelist):
        for node in nodelist:
            if node.nodeType == Node.ELEMENT_NODE:
                self.visit_element(node)

    def node_list_text_only(self, nodelist):
        result = []
        for node in nodelist:
            if node.nodeType == Node.TEXT_NODE:
                result.append(node.data)
            else:
                result.extend(self.node_list_text_only(node.childNodes))
        return "".join(result)

    def get_desc(self, nodelist):
        """ links can have either text or an image as description - we extract
            this from the child nodelist and return wiki markup.
        """
        markup = ''
        text = self.node_list_text_only(nodelist).replace("\n", " ").strip()
        if text:
            # found some text
            markup = text
        else:
            # search for an img / object
            for node in nodelist:
                if node.nodeType == Node.ELEMENT_NODE:
                    name = node.localName
                    if name == 'img':
                        markup = self._process_img(node) # XXX problem: markup containts auto-generated alt text with link target
                        break
                    elif name == 'object':
                        markup = self._process_object(node)
                        break
        return markup

    def process_page(self, node):
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                self.visit_element(i)
            elif i.nodeType == Node.TEXT_NODE: # if this is missing, all std text under a headline is dropped!
                txt = i.data.strip() # IMPORTANT: don't leave this unstripped or there will be wrong blanks
                if txt:
                    self.text.append(txt)
            #we use <pre class="comment"> now, so this is currently unused:
            #elif i.nodeType == Node.COMMENT_NODE:
            #    self.text.append(i.data)
            #    self.text.append("\n")

    def process_br(self, node):
        self.text.append(self.new_line) # without this, std multi-line text below some heading misses a whitespace
                                        # when it gets merged to float text, like word word wordword word word

    def process_heading(self, node):
        # Skip empty headings.
        if self.node_list_text_only(node.childNodes).strip() == '':
            return

        depth = int(node.localName[1])
        self.text.append(self.new_line)
        self.text.append("=" * depth + ' ')
        for i in node.childNodes:
            # allow some nested elements in headers
            if i.nodeType == Node.ELEMENT_NODE and i.localName in (
                'a', 'img', 'br', 'em', 'i', 'strong', 'b', 'span'):
                n = len(self.text)
                self.process_inline(i)
                # strip off any newlines that may have snuck in
                # the br element (forced linebreak) emits \\ in wiki, not \n
                self.text[n:] = [t.replace('\n', ' ') for t in self.text[n:]]
            else:
                self.text.append(
                    self.node_list_text_only([i]).replace('\n', ' ')
                )

        # Do we need closing?

        self.text.append(self.new_line)


    process_h1 = process_heading
    process_h2 = process_heading
    process_h3 = process_heading
    process_h4 = process_heading
    process_h5 = process_heading
    process_h6 = process_heading

    def _get_list_item_markup(self, list, listitem):
        name = list.localName
        widget = switch(name, ol='#', ul='*')
        indent = widget * (self.depth - 1)
        markup = '%s ' % widget

        return '', indent, markup

    def process_dl(self, node):
        self.depth += 1
        markup = ":: " # can there be a dl dd without dt?
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                name = i.localName
                if name == 'dt':
                    before, indent, markup = self._get_list_item_markup(node, i)
                    self.text.extend([before, indent])
                    text = self.node_list_text_only(i.childNodes)
                    self.text.append(text.replace("\n", " "))
                elif name == 'dd':
                    self.text.append(markup)
                    self.process_list_item(i, indent) # XXX no dt -> indent is undefined!!!
                else:
                    raise ConvertError("Illegal list element %s" % i.localName)
        self.depth -= 1
        if self.depth == 0:
            self.text.append(self.new_line_dont_remove)

    def process_list(self, node):
        self.depth += 1
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                name = i.localName
                if name == 'li':
                    before, indent, markup = self._get_list_item_markup(node, i)
                    self.text.extend([before, indent, markup])
                    self.process_list_item(i, indent)
                elif name in ('ol', 'ul', ):
                    self.process_list(i)
                elif name == 'dl':
                    self.process_dl(i)
                else:
                    raise ConvertError("Illegal list element %s" % i.localName)
        self.depth -= 1
        if self.depth == 0:
            self.text.append(self.new_line_dont_remove)

    process_ul = process_list
    process_ol = process_list

    def empty_paragraph_queue(self, nodelist, indent, need_indent):
        if need_indent:
            self.text.append(indent)
        for i in nodelist:
            if i.nodeType == Node.ELEMENT_NODE:
                if i.localName == 'br':
                    pass
                    #self.text.append('<<BR>>')
                else:
                    self.process_inline(i)
            elif i.nodeType == Node.TEXT_NODE:
                self.text.append(i.data.strip('\n').replace('\n', ' '))
        self.text.append(self.new_line)
        del nodelist[:]

    def process_list_item(self, node, indent):
        found = False
        need_indent = False
        pending = []
        for i in node.childNodes:
            name = i.localName

            if name in ('p', 'pre', 'ol', 'ul', 'dl', 'table', ) and pending:
                self.empty_paragraph_queue(pending, indent, need_indent)
                need_indent = True

            if name == 'p':
                if need_indent:
                    self.text.append(indent)
                self.process_paragraph_item(i)
                self.text.append(self.new_line)
                found = True
            elif name == 'pre':
                if need_indent:
                    self.text.append(indent)
                self.process_preformatted_item(i)
                found = True
            elif name in ('ol', 'ul', ):
                self.process_list(i)
                found = True
            elif name == 'dl':
                self.process_dl(i)
                found = True
            elif name == 'table':
                if need_indent:
                    self.text.append(indent)
                self.process_table(i)
                found = True
            elif name == 'br':
                pending.append(i)
            else:
                pending.append(i)

            if found:
                need_indent = True

        if pending:
            self.empty_paragraph_queue(pending, indent, need_indent)

    def process_blockquote(self, node):
        # XXX this does not really work. e.g.:
        # <bq>aaaaaa
        # <hr---------->
        # <bq>bbbbbb
        self.depth += 1
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                name = i.localName
                if name == 'p':
                    self.text.append(self.new_line)
                    self.text.append(" " * self.depth)
                    self.process_p(i)
                elif name == 'pre':
                    self.text.append(self.new_line)
                    self.text.append(" " * self.depth)
                    self.process_pre(i)
                elif name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', ):
                    self.process_heading(i)
                elif name in ('ol', 'ul', ):
                    self.process_list(i)
                elif name == 'dl':
                    self.process_dl(i)
                elif name == 'a':
                    self.process_a(i)
                elif name == 'img':
                    self.process_img(i)
                elif name == 'div':
                    self.visit_node_list_element_only(i.childNodes)
                elif name == 'blockquote':
                    self.process_blockquote(i)
                elif name == 'hr':
                    self.process_hr(i)
                elif name == 'br':
                    self.process_br(i)
                else:
                    self.process_blockquote(i)
                    #raise ConvertError("process_blockquote: Don't support %s element" % name)
        self.depth -= 1

    def process_inline(self, node):
        if node.nodeType == Node.TEXT_NODE:
            self.text.append(node.data.strip('\n').replace('\n', ' '))
            return

        # do we need to check for Node.ELEMENT_NODE and return (do nothing)?
        name = node.localName # can be None for DOM Comment nodes
        if name is None:
            return

        # unsupported tags
        if name in (u'title', u'meta', u'style'):
            return

        if name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', ): # headers are not allowed here (e.g. inside a ul li),
            text = self.node_list_text_only(node.childNodes).strip() # but can be inserted via the editor
            self.text.append(text)                          # so we just drop the header markup and keep the text
            return

        func = getattr(self, "process_%s" % name, None)
        if func:
            func(node)
            return

        command_close = None
        if name in ('em', 'i', ):
            command = "//"
        elif name in ('strong', 'b', ):
            command = "**"
        elif name == 'u':
            command = "__"
        elif name == 'big':
            command = "~+"
            command_close = "+~"
        elif name == 'small':
            command = "~-"
            command_close = "-~"
        elif name == 'strike':
            command = "--("
            command_close = ")--"
        elif name == 'sub':
            command = ",,"
        elif name == 'sup':
            command = "^"
        elif name in ('area', 'center', 'code', 'embed', 'fieldset', 'font', 'form', 'iframe', 'input', 'label', 'link', 'map',
                      'meta', 'noscript', 'option', 'script', 'select', 'textarea', 'wbr'):
            command = "" # just throw away unsupported elements
        else:
            command = ''
        # TODO(marius): log these
        #raise ConvertError("process_inline: Don't support %s element" % name)

        # Don't process commands on lone <br>s that editors sometimes
        # produce for us.
        if (not command
            or len(node.childNodes) != 1
            or node.childNodes[0].localName != 'br'):

            self.text.append(command)
            for i in node.childNodes:
                if command and len(node.childNodes) == 1:
                    self.process_inline(i)
                else:
                    if i.localName == 'br':
                        pass
                        # dont make a real \n because that breaks tables
                        #self.text.append('<<BR>>')
                    else:
                        self.process_inline(i)
            if command_close:
                command = command_close
            self.text.append(command)

    def process_span(self, node):
        # process span tag for firefox3
        node_style = node.getAttribute("style")

        is_strike = node.getAttribute("class") == "strike"
        is_strike = is_strike or "line-through" in node_style
        is_strong = "bold" in node_style
        is_italic = "italic" in node_style
        is_underline = "underline" in node_style
        is_comment = node.getAttribute("class") == "comment"

        # start tag
        if is_comment:
            self.text.append("/* ")
        if is_strike:
            self.text.append("--(")
        if is_strong:
            self.text.append("**")
        if is_italic:
            self.text.append("//")
        if is_underline:
            self.text.append("__")

        # body
        for i in node.childNodes:
            self.process_inline(i)

        # end tag
        if is_underline:
            self.text.append("__")
        if is_italic:
            self.text.append("//")
        if is_strong:
            self.text.append("**")
        if is_strike:
            self.text.append(")--")
        if is_comment:
            self.text.append(" */")

    def process_div(self, node):
        # process indent
        self._process_indent(node)

        # ignore div tags - just descend
        for i in node.childNodes:
            self.visit(i)

    def process_tt(self, node):
        text = self.node_list_text_only(node.childNodes).replace("\n", " ")
        if node.getAttribute("class") == "backtick":
            self.text.append("`%s`" % text)
        else:
            self.text.append("{{{%s}}}" % text)

    def process_hr(self, node):
        if node.hasAttribute("class"):
            class_ = node.getAttribute("class")
        else:
            class_ = "hr0"
        if class_.startswith("hr") and class_[2] in "123456":
            length = int(class_[2]) + 4
        else:
            length = 4
        self.text.extend([self.new_line, "-" * length, self.new_line])

    def process_p(self, node):
        # process indent
        self._process_indent(node)
        self.process_paragraph_item(node)
        self.text.append("\n\n") # do not use self.new_line here!

    def _process_indent(self, node):
        # process indent
        node_style = node.getAttribute("style")
        match = re.match(r"margin-left:\s*(\d+)px", node_style)
        if match:
            left_margin = int(match.group(1))
            indent_depth = int(left_margin / 40)
            if indent_depth > 0:
                self.text.append(' . ')

    def process_paragraph_item(self, node):
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                self.process_inline(i)
            elif i.nodeType == Node.TEXT_NODE:
                self.text.append(i.data.strip('\n').replace('\n', ' '))

    def process_pre(self, node):
        self.process_preformatted_item(node)
        self.text.append(self.new_line)

    def process_preformatted_item(self, node):
        if node.hasAttribute("class"):
            class_ = node.getAttribute("class")
        else:
            class_ = None
        if class_ == "comment": # we currently use this for stuff like ## or #acl
            for i in node.childNodes:
                if i.nodeType == Node.TEXT_NODE:
                    self.text.append(i.data.replace('\n', ''))
                elif i.localName == 'br':
                    self.text.append(self.new_line)
                else:
                    pass
        else:
            content_buffer = []
            longest_inner_formater = ''
            bang_args = ''
            delimiters = []

            """
            below code fixed for MoinMoinBugs/GuiEditorCantNest bug
            this has problem when outer delimiter has two more { than inside one
            e.g. {{{{{{ {{{ foo }}} }}}}}}  --> {{{{ {{{ foo }}} }}}}
                   {{{foo {{{ }}} foo}}} --> {{{{ {{{ }}} }}}}
            """

            for i in node.childNodes:
                if i.nodeType == Node.TEXT_NODE:
                    # get longest pre tag({{{ or }}}) from content
                    delimiters.extend(re.compile("((?u){+)").findall(i.data))
                    delimiters.extend(re.compile("((?u)}+)").findall(i.data))
                    # when first line is empty, start iteration second line of i.data
                    data_lines = i.data.rstrip().split('\n')
                    if data_lines[0].strip() == '':
                        data_lines = data_lines[1:]
                    for line in data_lines:
                        if line.strip().startswith('#!'):
                            if bang_args == '':
                                bang_args = line.strip()
                            else:
                                content_buffer.extend([line, self.new_line])
                        else:
                            content_buffer.extend([line, self.new_line])
                elif i.localName == 'br':
                    content_buffer.append(self.new_line_dont_remove)
                else:
                    pass

            if delimiters:
                longest_inner_formater = max(delimiters)

            if (len(longest_inner_formater) >= 3):
                self.text.extend([("{" * (len(longest_inner_formater) + 1)) + bang_args, \
                                      self.new_line])
                self.text.extend(content_buffer)
                self.text.extend(["}" * (len(longest_inner_formater) + 1), \
                                      self.new_line])
            else:
                self.text.extend(["{{{"+bang_args, self.new_line])
                self.text.extend(content_buffer)
                self.text.extend(["}}}", self.new_line])

    _alignment = {"left": "(",
                  "center": ":",
                  "right": ")",
                  "top": "^",
                  "bottom": "v"}

    def _check_length(self, value):
        try:
            int(value)
            return value + 'px'
        except ValueError:
            return value

    def _get_color(self, node, prefix):
        if node.hasAttribute("bgcolor"):
            value = node.getAttribute("bgcolor")
            match = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", value)
            if match:
                value = '#%X%X%X' % (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            else:
                match = re.match(r"#[0-9A-Fa-f]{6}", value)
            if not prefix and match:
                result = value
            else:
                result = '%sbgcolor="%s"' % (prefix, value)
        else:
            result = ''
        return result

    def _table_style(self, node):
        # TODO: attrs = get_attrs(node)
        result = []
        result.append(self._get_color(node, 'table'))
        if node.hasAttribute("width"):
            value = node.getAttribute("width")
            result.append('tablewidth="%s"' % self._check_length(value))
        if node.hasAttribute("height"):
            value = node.getAttribute("height")
            result.append('tableheight="%s"' % self._check_length(value))
        if node.hasAttribute("align"):
            value = node.getAttribute("align")
            result.append('tablealign="%s"' % value)
        if node.hasAttribute("style"):
            result.append('tablestyle="%s"' % node.getAttribute("style"))
        if node.hasAttribute("class"):
            result.append('tableclass="%s"' % node.getAttribute("class"))
        return " ".join(result).strip()

    def _row_style(self, node):
        # TODO: attrs = get_attrs(node)
        result = []
        result.append(self._get_color(node, 'row'))
        if node.hasAttribute("style"):
            result.append('rowstyle="%s"' % node.getAttribute("style"))
        if node.hasAttribute("class"):
            result.append('rowclass="%s"' % node.getAttribute("class"))
        return " ".join(result).strip()

    def _cell_style(self, node):
        # TODO: attrs = get_attrs(node)
        if node.hasAttribute("rowspan"):
            rowspan = ("|%s" % node.getAttribute("rowspan"))
        else:
            rowspan = ""

        if node.hasAttribute("colspan"):
            colspan = int(node.getAttribute("colspan"))
        else:
            colspan = 1

        spanning = rowspan or colspan > 1

        align = ""
        result = []
        result.append(self._get_color(node, ''))
        if node.hasAttribute("align"):
            value = node.getAttribute("align")
            if not spanning or value != "center":
                # ignore "center" in spanning cells
                align += self._alignment.get(value, "")
        if node.hasAttribute("valign"):
            value = node.getAttribute("valign")
            if not spanning or value != "center":
                # ignore "center" in spanning cells
                align += self._alignment.get(value, "")
        if node.hasAttribute("width"):
            value = node.getAttribute("width")
            if value[-1] == "%":
                align += value
            else:
                result.append('width="%s"' % self._check_length(value))
        if node.hasAttribute("height"):
            value = node.getAttribute("height")
            result.append('height="%s"' % self._check_length(value))
        if node.hasAttribute("class"):
            result.append('class="%s"' % node.getAttribute("class"))
        if node.hasAttribute("id"):
            result.append('id="%s"' % node.getAttribute("id"))
        if node.hasAttribute("style"):
            result.append('style="%s"' % node.getAttribute("style"))

        if align:
            result.insert(0, "%s" % align)
        result.append(rowspan)
        return " ".join(result).strip()

    def process_table(self, node, style=""):
        if self.depth == 0:
            self.text.append(self.new_line)
        self.new_table = True
        style += self._table_style(node)
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                name = i.localName
                if name == 'tr':
                    self.process_table_record(i, style)
                    style = ""
                elif name in ('thead', 'tbody', 'tfoot'):
                    self.process_table(i, style)
                elif name == 'caption':
                    self.process_caption(node, i, style)
                    style = ''
                elif name in ('col', 'colgroup', 'strong', ):
                    pass # we don't support these, but we just ignore them
                else:
                    pass
                # raise ConvertError("process_table: Don't support %s element" % name)
            #else:
            #    raise ConvertError("Unexpected node: %r" % i)
        self.text.append(self.new_line_dont_remove)

    def process_caption(self, table, node, style=""):
        # get first row
        for i in table.childNodes:
            if i.localName in ('thead', 'tbody', 'tfoot'): # XXX is this correct?
            #if i.localName == 'tbody': (old version)
                for i in i.childNodes:
                    if i.localName == 'tr':
                        break
                break
            elif i.localName == 'tr':
                break
        # count columns
        if i.localName == 'tr':
            colspan = 0
            for td in i.childNodes:
                if not td.nodeType == Node.ELEMENT_NODE:
                    continue
                span = td.getAttribute('colspan')
                try:
                    colspan += int(span)
                except ValueError:
                    colspan += 1
        else:
            colspan = 1
        text = self.node_list_text_only(node.childNodes).replace('\n', ' ').strip()
        if text:
            if style:
                style = '<%s>' % style
            self.text.extend(["%s%s'''%s'''||" % ('||' * colspan, style, text), self.new_line_dont_remove])

    def process_table_data(self, node, style=""):
        if node.hasAttribute("colspan"):
            colspan = int(node.getAttribute("colspan"))
        else:
            colspan = 1
        self.text.append("|" * colspan)

        style += self._cell_style(node)
        if style:
            self.text.append("<%s>" % style)

        found = False
        for i in node.childNodes:
            name = i.localName
            if name == 'p':
                self.process_paragraph_item(i)
                self.text.append(self.white_space)
                found = True
        if not found:
            for i in node.childNodes:
                name = i.localName
                if i.nodeType == Node.ELEMENT_NODE:
                    if name == 'br':
                        # if we get a br for a cell from e.g. cut and
                        # paste from OOo or if someone simulates a
                        # list by enter in a cell it should be
                        # appended as macro BR.

                        # self.text.append('<<BR>>')
                        found = True
                        continue
                    else:
                        self.process_inline(i)
                        found = True
                elif i.nodeType == Node.TEXT_NODE:
                    data = i.data.strip('\n').replace('\n', ' ')
                    if data:
                        found = True
                        self.text.append(data)
        if not found:
            self.text.append(" ")

    def process_table_record(self, node, style=""):
        if not self.new_table:
            self.text.append(" " * self.depth)
        else:
            self.new_table = False
        style += self._row_style(node)
        for i in node.childNodes:
            if i.nodeType == Node.ELEMENT_NODE:
                name = i.localName
                if name in ('td', 'th', ):
                    self.process_table_data(i, style=style)
                    style = ""
                else:
                    pass
                    #raise ConvertError("process_table_record: Don't support %s element" % name)
        self.text.extend(["|", self.new_line_dont_remove])

    def process_a(self, node):
        attrs = get_attrs(node)

        title = attrs.pop('title', '')
        href = attrs.pop('href', None)
        css_class = attrs.get('class')
        
        if not href:
            return

        href = wikiutil.url_unquote(href)
        desc = self.get_desc(node.childNodes)

        res = self.resolve_url(href)
        if res is None:
            raise sym.invalid_url.exc()
        elif isinstance(res, tuple):
            urltype, wiki, page = res
            if urltype == sym.page:
                # Ok, we got a wiki link.
                self.text.append('[[%s:%s|%s]]' % (wiki, page, desc))
            else:
                raise sym.wtf_XXX.exc()
        else:
            if res != desc:
                extra = '|%s' % desc
            else:
                extra = ''

            self.text.append('[[%s%s]]' % (res, extra))

    def process_img(self, node):
        markup = self._process_img(node)
        self.text.append(markup)

    def _process_img(self, node):
        attrs = get_attrs(node)
        src = attrs.pop('src', None)
        if not src:
            return ''
        src = wikiutil.url_unquote(src)

        res = self.resolve_url(src)        
        if res is None:
            raise sym.invalid_image.exc()
        if isinstance(res, tuple):
            urltype, wiki_slug, page_slug, slug = res
            if urltype == sym.attachment:
                return '<<img %s>>' % slug
            elif urltype == sym.image:
                args = slug
                # TODO(tw): Deal with links for images from other wikis
                # probably using dyn vars to get current wiki from request obj
                try:
                    wiki = Wiki.objects.get(pk=wiki_slug)
                    page = wiki.page_set.get(slug=page_slug)
                    photo = page.photos.get(slug=slug)
                except ObjectDoesNotExist:
                    # TODO:(tw) Allow linking to an image that doesn't exist?
                    raise sym.wtf_XXX.exc()

                try:
                    # Reconstruct (and validate) the original args to this
                    # image from a special query string
                    cgi_params = cgi.parse_qs(urlparse.urlparse(src).query)
                    wiki_attrs = parse_img_attributes(photo,
                            cgi_params['wiki_img_args'][0].split('|'))
                except:
                    # Not sure if it is better to complain loudly at this
                    # point or just fall back to defaults
                    wiki_attrs = storage()

                try:
                    # Try to get the image size from the element itself
                    size = (int(attrs['width']), int(attrs['height']))
                except:
                    # Otherwise get it from the previous wiki arguments
                    size = wiki_attrs.get('size', None)

                if size and size != (photo.width, photo.height):
                    scaled_height = photo.get_scaled_dimensions(size[0])[1]
                    if scaled_height == size[1]:
                        # Default width is what the width would be if no
                        # dimensions were specified                        
                        if wiki_attrs.get('type', '') in ('thumb',
                                'thumbnail'):
                            default_width = default_thumb_width
                        else:
                            default_width = max_image_width
                        if (size[0] != default_width):
                            # Height can be derived from width * aspect.
                            # Specify width only.
                            args += '|%dpx' % size[0]
                    else:
                        # Height and width both need to be specified.
                        args += '|%dx%dpx' % (size[0], size[1])

                for attr in ('type', 'align', 'alt', 'caption'):
                    if attr in wiki_attrs:
                        args += '|%s' % wiki_attrs[attr]
                return '<<img %s>>' % args
            else:
                raise sym.wtf_XXX.exc()
        else:
            return '{{%s}}' % res

    def process_object(self, node):
        markup = self._process_object(node)
        self.text.append(markup)

    def _process_object(self, node):
        attrs = get_attrs(node)
        markup = ''
        data = attrs.pop('data', None)
        if data:
            data = wikiutil.url_unquote(data)

            desc = self.get_desc(node.childNodes)
            if desc:
                desc = '|' + desc

            params = ','.join(['%s="%s"' % (k, v) for k, v in attrs.items()])
                               # if k in ('width', 'height', )])
            if params:
                params = '|' + params
                if not desc:
                    desc = '|'
            markup = "{{%s%s%s}}" % (data, desc, params)
        return markup
        # TODO: for target PAGES, use some code from process_a to get the pagename from URL
        # TODO: roundtrip attachment: correctly
        # TODO: handle object's content better?

def get_attrs(node):
    """ get the attributes of <node> into an easy-to-use dict """
    attrs = {}
    for attr_name in node.attributes.keys():
        # get attributes of style element
        if attr_name == "style":
            for style_element in node.attributes.get(attr_name).nodeValue.split(';'):
                if style_element.strip() != '':
                    style_elements = style_element.split(':')
                    if len(style_elements) == 2:
                        attrs[style_elements[0].strip()] = style_elements[1].strip()
        # get attributes without style element
        else:
            attrs[attr_name] = node.attributes.get(attr_name).nodeValue
    return attrs


def parse(text):
    text = u'<?xml version="1.0"?>%s%s' % (dtd, text)
    # TODO(marius): should we standardize on anything?
    text = text.encode('utf-8')
    try:
        return xml.dom.minidom.parseString(text)
    except xml.parsers.expat.ExpatError, msg:
        # this sometimes crashes when it should not, so save the stuff to analyze it:
#         logname = os.path.join(request.cfg.data_dir, "expaterror.log")
#         f = file(logname, "w")
#         f.write(text)
#         f.write("\n" + "-"*80 + "\n" + str(msg))
#         f.close()
#    raise ConvertError('ExpatError: %s (see dump in %s)' % (msg, logname))
        raise

def convert(pagename, text, resolve_url):
    # Due to expat needing explicitly set namespaces, we set these
    # here to allow pasting from Word / Excel without issues.  If you
    # encounter 'ExpatError: unbound prefix', try adding the namespace
    # to the list.
    namespace = [u'xmlns:o="urn:schemas-microsoft-com:office:office"',
                 u'xmlns:x="urn:schemas-microsoft-com:office:excel"',
                 u'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"',
                 u'xmlns:c="urn:schemas-microsoft-com:office:component:spreadsheet"',
                 u'xmlns:s="uuid:BDC6E3F0-6DA3-11d1-A2A3-00AA00C14882"',
                 u'xmlns:dt="uuid:C2F41010-65B3-11d1-A29F-00AA00C14882"',
                 u'xmlns:rs="urn:schemas-microsoft-com:rowset"',
                 u'xmlns:z="#RowsetSchema"',
                 u'xmlns:x2="http://schemas.microsoft.com/office/excel/2003/xml"',
                 u'xmlns:sl="http://schemas.microsoft.com/schemaLibrary/2003/core"',
                 u'xmlns:aml="http://schemas.microsoft.com/aml/2001/core"',
                 u'xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"',
                 u'xmlns:wx="http://schemas.microsoft.com/office/word/2003/auxHint"',
                 u'xmlns:w10="urn:schemas-microsoft-com:office:word"',
                 u'xmlns:v="urn:schemas-microsoft-com:office:vml"']
    text = u'<page %s>%s</page>' % (' '.join(namespace), text)
    tree = parse(text)
    strip_whitespace().do(tree)
    text = convert_tree(pagename, resolve_url).do(tree)
    text = '\n'.join([s.rstrip() for s in text.splitlines()] + ['']) # remove trailing blanks
    return text
