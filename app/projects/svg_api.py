class SheetSVG(object):

    def __init__(self, width, height, cutback):
        self.cutback = cutback
        self.width = width
        self.height = height
        self.fill = "none"
        self.stroke = "none"

    @property
    def widthHalf(self):
        return self.width >> 1

    @property
    def folioX(self):
        return self.width - 36

    @property
    def folioY(self):
        return self.height - 36

    @property
    def fill_stroke(self):
        return " fill=\"none\" stroke=\"none\" "

    @property
    def xywh(self):
        return " y=\"0\" x=\"0\" width=\"" + str(self.width) + "\" height=\"" + str(self.height) + "\" "

    @property
    def xywhLeft(self):
        return " y=\"0\" x=\"0\" width=\"" + str(self.widthHalf) + "\" height=\"" + str(self.height) + "\" "

    # Full spread red bleed outline
    @property
    def xywhBleed(self):
        return " y=\"9\" x=\"9\" width=\"" + str(self.width - 18) + "\" height=\"" + str(self.height - 18) + "\" "

    # Left blue box
    @property
    def xywhViewLeft(self):
        return " y=\"36\" x=\"36\" width=\"" + str(self.widthHalf - 36 - 9) + "\" height=\"" + str(self.height - 72) + "\" "

    # Left green box
    @property
    def xywhCutLeft(self):
        return " y=\"18\" x=\"18\" width=\"" + str(self.widthHalf - 18) + "\" height=\"" + str(self.height - 36) + "\" "

    # Right blue box
    @property
    def xywhViewRight(self):
        return " y=\"36\" x=\"" + str(self.widthHalf + 9) + "\" width=\"" + str(self.widthHalf - 36 - 9) + "\" height=\"" + str(self.height - 72) + "\" "

    # Right green box
    @property
    def xywhCutRight(self):
        return " y=\"18\" x=\"" + str(self.widthHalf) + "\" width=\"" + str(self.widthHalf - 18) + "\" height=\"" + str(self.height - 36) + "\" "

    # Full spread blue box (outline)
    @property
    def xywhViewFull(self):
        return " y=\"0\" x=\"0\" width=\"" + str(self.width) + "\" height=\"" + str(self.height) + "\" "

    @property
    def xywhRight(self):
        return " y=\"0\" x=\"" + str(self.widthHalf) + "\" width=\"" + str(self.widthHalf) + "\" height=\"" + str(self.height) + "\" "

    @property
    def insetWH1(self):
        return " width=\"" + str(self.widthHalf - 6) + "\" height=\"" + str(self.height - 12) + "\" "

    @property
    def insetWH2(self):
        return " width=\"" + str(self.widthHalf - 42) + "\" height=\"" + str(self.height - 60) + "\" "

    @property
    def folioText(self):
        return "<text height=\"10\" width=\"100\" y=\"" + str(self.folioY) + "\" x=\"32\" stroke-width=\"0\" fill=\"none\""

    @property
    def header(self):
        return "<svg xmlns=\"http://www.w3.org/2000/svg\" xmlns:se=\"http://svg-edit.googlecode.com\" " + \
            "xmlns:lyb=\"http://www.myyear.com\" width=\"" + str(self.width) + "\" height=\"" + str(self.height) + "\">\n"

    @property
    def bgAndL1(self):
        return "<g id=\"background_layer\"><title>Background</title>\n" + \
            "<g lyb:dropTarget=\"g\" id=\"background_group_F\">" + \
            "<rect lyb:background=\"F\" lyb:dropTarget=\"border\" id=\"background_F\"" + self.xywh + self.fill_stroke + "/></g>\n" + \
            "<g lyb:dropTarget=\"g\" id=\"background_group_L\">" + \
            "<rect lyb:background=\"L\" lyb:dropTarget=\"border\" id=\"background_L\"" + self.xywhLeft + self.fill_stroke + "/></g>\n" + \
            "<g lyb:dropTarget=\"g\" id=\"background_group_R\">" + \
            "<rect lyb:background=\"R\" lyb:dropTarget=\"border\" id=\"background_R\"" + self.xywhRight + self.fill_stroke + "/></g>\n" + \
            "</g>\n<g id=\"layer_1\"><title>Layer 1</title></g>\n"

    @property
    def safetyLeft(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"guide_LEFT\"><title>Safety Zone LEFT</title>\n" + \
            "<rect id=\"guide_FULL_rect\"" + self.xywhViewFull + "stroke=\"#0000FF\" fill=\"none\"/>\n" + \
            "<rect id=\"guide_LEFT_CUT_rect\"" + self.xywhCutLeft + "stroke=\"#00FF00\" fill=\"none\"/>\n" + \
            "<rect id=\"guide_LEFT_SAFETY_rect\"" + self.xywhViewLeft + "stroke=\"#0000FF\" fill=\"none\"/>\n</g>\n"

    @property
    def safetyLeftCutback(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"guide_LEFT\"><title>Safety Zone LEFT</title>\n" + \
            "<rect id=\"guide_cutback\" height=\"" + str(self.height) + "\" y=\"0\" x=\"" + str(int(self.widthHalf) - 18) + "\" stroke=\"none\" stroke-width=\"0\" opacity=\"1\" fill=\"#ffffff\" width=\"36\"/>\n" + \
            "<rect id=\"guide_FULL_rect\"" + self.xywhViewFull + "stroke=\"#0000FF\" fill=\"none\"/>\n" + \
            "<rect id=\"guide_LEFT_CUT_rect\"" + self.xywhCutLeft + "stroke=\"#00FF00\" fill=\"none\"/>\n" + \
            "<rect id=\"guide_LEFT_SAFETY_rect\"" + self.xywhViewLeft + "stroke=\"#0000FF\" fill=\"none\"/>\n</g>\n"

    @property
    def safetyRight(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"guide_RIGHT\"><title>Safety Zone RIGHT</title>\n" + \
            "<rect id=\"guide_RIGHT_CUT_rect\"" + self.xywhCutRight + "stroke=\"#00FF00\" fill=\"none\"/>\n" + \
            "<rect id=\"guide_RIGHT_SAFETY_rect\"" + self.xywhViewRight + "stroke=\"#0000FF\" fill=\"none\"/>\n</g>\n"

    @property
    def emptyLeft(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"empty_page_left\"><title>Empty Page LEFT</title>\n" + \
            "<rect id=\"guide_LEFT_rect\"" + self.xywhLeft + "fill=\"#363637\"/></g>\n"

    @property
    def emptyLeftCutback(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"empty_page_left\"><title>Empty Page LEFT</title>\n" + \
            "<rect id=\"guide_cutback\" height=\"" + str(self.height) + "\" y=\"0\" x=\"" + str(int(self.widthHalf) - 18) + "\" stroke=\"none\" stroke-width=\"0\" opacity=\"1\" fill=\"#ffffff\" width=\"36\"/>\n" + \
            "<rect id=\"guide_LEFT_rect\"" + self.xywhLeft + "fill=\"#363637\"/></g>\n"

    @property
    def emptyRight(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"empty_page_right\"><title>Empty Page RIGHT</title>\n" + \
            "<rect id=\"guide_RIGHT_rect\"" + self.xywhRight + "fill=\"#363637\"/></g>\n"

    @property
    def ggLayer(self):
        return "<g se:guide=\"true\" se:lock=\"L\" id=\"gg_layer\"><title>MY Grid and Guides Layer</title>\n" + \
            "<rect id=\"guide_FULL_BLEED_rect\"" + self.xywhBleed + "stroke=\"#FF0000\" stroke-width=\"18\" opacity=\"0.5\" fill=\"none\"/></g>\n"

    @property
    def folioLayer(self):
        return "<g se:lock=\"L\" id=\"folio_layer\"><title>Folio Layer</title>\n" + \
            "<text height=\"10\" width=\"100\" y=\"" + str(self.folioY) + "\" x=\"36\" stroke-width=\"0\" fill=\"none\" id=\"ft_l\">" + \
            "<tspan xml:space=\"preserve\" id=\"fts_l\" fill=\"#000000\" fill-opacity=\"1\" font-family=\"Limerick\" font-size=\"10\"" + \
            " font-style=\"normal\" font-weight=\"normal\" opacity=\"1\" se:leadingwhitespacecount=\"0\" dy=\"0\" x=\"36\">LEFT_FOLIO</tspan></text>" + \
            "<text height=\"10\" width=\"100\" y=\"" + str(self.folioY) + "\" x=\"" + str(self.folioX) + "\" text-anchor=\"end\" stroke-width=\"0\" fill=\"none\" id=\"ft_r\">" + \
            "<tspan xml:space=\"preserve\" id=\"fts_r\" fill=\"#000000\" fill-opacity=\"1\" font-family=\"Limerick\" font-size=\"10\"" + \
            " font-style=\"normal\" font-weight=\"normal\" opacity=\"1\" se:leadingwhitespacecount=\"0\" dy=\"0\" x=\"" + str(self.folioX) + "\">RIGHT_FOLIO</tspan></text>" + \
            "</g>\n</svg>"

    @property
    def fullSVG(self):
        return self.header + self.bgAndL1 + self.safetyLeft + self.safetyRight + self.ggLayer + \
               self.folioLayer

    @property
    def leftPageSVG(self):
        if self.cutback is True:
            return self.header + self.bgAndL1 + self.safetyLeftCutback + self.emptyRight + self.ggLayer + self.folioLayer
        else:
            return self.header + self.bgAndL1 + self.safetyLeft + self.emptyRight + self.ggLayer + self.folioLayer

    @property
    def rightPageSVG(self):
        if self.cutback is True:
            return self.header + self.bgAndL1 + self.emptyLeftCutback + self.safetyRight + self.ggLayer + self.folioLayer
        else:
            return self.header + self.bgAndL1 + self.emptyLeft + self.safetyRight + self.ggLayer + self.folioLayer

    @property
    def template(self):
        return [self.leftPageSVG, self.fullSVG, self.rightPageSVG]

    # new_8_full = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:lyb="http://www.myyear.com" xmlns:se="http://svg-edit.googlecode.com" width="1296" height="828" preserveAspectRatio="xMinYMin meet"><g id="background_layer"><title>Background</title><g lyb:dropTarget="g" id="background_group_F"><rect lyb:background="F" lyb:dropTarget="border" y="0" x="0" width="1260" stroke-width="0" stroke="#000000" id="background_F" height="828" fill-opacity="0" fill="#000000"/></g><g lyb:dropTarget="g" id="background_group_L"><rect lyb:background="L" lyb:dropTarget="border" y="0" x="0" width="630" stroke-width="0" stroke="#000000" id="background_L" height="828" fill-opacity="0" fill="#000000"/></g><g lyb:dropTarget="g" id="background_group_R"><rect lyb:background="R" lyb:dropTarget="border" y="0" x="630" width="630" stroke-width="0" stroke="#000000" id="background_R" height="828" fill-opacity="0" fill="#000000"/></g></g><g id="layer_1"><title>Layer 1</title></g><g lyb:zHeight="1125" lyb:zWidth="875" lyb:zx="0" lyb:zy="0" se:guide="true" se:lock="L" id="guide_LEFT"><title>Safety Zone LEFT</title><rect y="0" x="0" width="1260" stroke="#0000ff" id="guide_LEFT_BLEED_rect" height="828" fill="none"/><rect y="18" x="18" width="612" stroke="#00ff00" id="guide_LEFT_SAFETY_rect" height="792" fill="none"/><rect y="36" x="36" width="585" stroke="#0000ff" id="guide_LEFT_SPACER_rect" height="756" fill="none"/></g><g lyb:zHeight="1125" lyb:zWidth="875" lyb:zx="875" lyb:zy="0" se:guide="true" se:lock="L" id="guide_RIGHT"><title>Safety Zone RIGHT</title><rect y="18" x="630" width="612" stroke="#00ff00" id="guide_RIGHT_SAFETY_rect" height="792" fill="none"/><rect y="36" x="639" width="585" stroke="#0000ff" id="guide_LEFT_SPACER_rect" height="756" fill="none"/><rect y="9" x="9" width="1242" stroke="#ff0000" id="guide_FULL_CUT_rect" height="810" fill="none" stroke-width="18" opacity="0.5" /></g><g id="gg_layer"><title>MY Grid and Guides Layer</title></g><g se:lock="L" id="folio_layer"><title>Folio Layer</title><text height="10" width="100" y="792" x="36" stroke-width="0" fill="none" id="ft_l"><tspan xml:space="preserve" id="fts_l" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0">2</tspan></text><text height="10" width="100" y="792" x="1224" text-anchor="end" stroke-width="0" fill="none" id="ft_r"><tspan xml:space="preserve" id="fts_r" fill="#000000" fill-opacity="1" font-family="Limerick" font-size="10" font-style="normal" font-weight="normal" opacity="1" se:leadingwhitespacecount="0" dy="0">3</tspan></text></g></svg>"""
