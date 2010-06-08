<!-- Extract the TIMEX3 elements and print just their text contents. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:strip-space elements="*"/>
<xsl:output method="text"/>

<xsl:template match="/TimeML">
  <TimeML>
    <xsl:apply-templates select="TIMEX3"/>
  </TimeML>
</xsl:template>

<xsl:template match="TIMEX3">
  <xsl:value-of select="normalize-space(.)"/><xsl:text>
</xsl:text>
</xsl:template>
</xsl:stylesheet>
