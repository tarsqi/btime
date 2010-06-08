<!-- Extract the TIMEX3 elements and print them using defaults. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:strip-space elements="*"/>
<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

<xsl:template match="/TimeML">
  <TimeML>
    <xsl:apply-templates select="TIMEX3"/>
  </TimeML>
</xsl:template>

<xsl:template match="TIMEX3">
  <TIMEX3>
    <xsl:apply-templates select="@*"/>
    <xsl:value-of select="normalize-space(.)"/>
  </TIMEX3>
</xsl:template>

<xsl:template match="TIMEX3/@*">
  <xsl:copy/>
</xsl:template>

<xsl:template match="TIMEX3/@functionInDocument">
  <xsl:if test=".!='NONE'"><xsl:copy/></xsl:if>
</xsl:template>

<xsl:template match="TIMEX3/@temporalFunction">
  <xsl:if test=".!='false'"><xsl:copy/></xsl:if>
</xsl:template>
</xsl:stylesheet>
