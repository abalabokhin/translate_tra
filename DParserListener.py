# Generated from DParser.g4 by ANTLR 4.9.2
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .DParser import DParser
else:
    from DParser import DParser

# This class defines a complete listener for a parse tree produced by DParser.
class DParserListener(ParseTreeListener):

    # Enter a parse tree produced by DParser#dFileRule.
    def enterDFileRule(self, ctx:DParser.DFileRuleContext):
        pass

    # Exit a parse tree produced by DParser#dFileRule.
    def exitDFileRule(self, ctx:DParser.DFileRuleContext):
        pass


    # Enter a parse tree produced by DParser#beginDAction.
    def enterBeginDAction(self, ctx:DParser.BeginDActionContext):
        pass

    # Exit a parse tree produced by DParser#beginDAction.
    def exitBeginDAction(self, ctx:DParser.BeginDActionContext):
        pass


    # Enter a parse tree produced by DParser#appendDAction.
    def enterAppendDAction(self, ctx:DParser.AppendDActionContext):
        pass

    # Exit a parse tree produced by DParser#appendDAction.
    def exitAppendDAction(self, ctx:DParser.AppendDActionContext):
        pass


    # Enter a parse tree produced by DParser#appendEarlyDAction.
    def enterAppendEarlyDAction(self, ctx:DParser.AppendEarlyDActionContext):
        pass

    # Exit a parse tree produced by DParser#appendEarlyDAction.
    def exitAppendEarlyDAction(self, ctx:DParser.AppendEarlyDActionContext):
        pass


    # Enter a parse tree produced by DParser#chainDAction.
    def enterChainDAction(self, ctx:DParser.ChainDActionContext):
        pass

    # Exit a parse tree produced by DParser#chainDAction.
    def exitChainDAction(self, ctx:DParser.ChainDActionContext):
        pass


    # Enter a parse tree produced by DParser#interjectDAction.
    def enterInterjectDAction(self, ctx:DParser.InterjectDActionContext):
        pass

    # Exit a parse tree produced by DParser#interjectDAction.
    def exitInterjectDAction(self, ctx:DParser.InterjectDActionContext):
        pass


    # Enter a parse tree produced by DParser#interjectCopyTransDAction.
    def enterInterjectCopyTransDAction(self, ctx:DParser.InterjectCopyTransDActionContext):
        pass

    # Exit a parse tree produced by DParser#interjectCopyTransDAction.
    def exitInterjectCopyTransDAction(self, ctx:DParser.InterjectCopyTransDActionContext):
        pass


    # Enter a parse tree produced by DParser#extendTopBottomDAction.
    def enterExtendTopBottomDAction(self, ctx:DParser.ExtendTopBottomDActionContext):
        pass

    # Exit a parse tree produced by DParser#extendTopBottomDAction.
    def exitExtendTopBottomDAction(self, ctx:DParser.ExtendTopBottomDActionContext):
        pass


    # Enter a parse tree produced by DParser#addStateTriggerDAction.
    def enterAddStateTriggerDAction(self, ctx:DParser.AddStateTriggerDActionContext):
        pass

    # Exit a parse tree produced by DParser#addStateTriggerDAction.
    def exitAddStateTriggerDAction(self, ctx:DParser.AddStateTriggerDActionContext):
        pass


    # Enter a parse tree produced by DParser#addTransTriggerDAction.
    def enterAddTransTriggerDAction(self, ctx:DParser.AddTransTriggerDActionContext):
        pass

    # Exit a parse tree produced by DParser#addTransTriggerDAction.
    def exitAddTransTriggerDAction(self, ctx:DParser.AddTransTriggerDActionContext):
        pass


    # Enter a parse tree produced by DParser#addTransActionDAction.
    def enterAddTransActionDAction(self, ctx:DParser.AddTransActionDActionContext):
        pass

    # Exit a parse tree produced by DParser#addTransActionDAction.
    def exitAddTransActionDAction(self, ctx:DParser.AddTransActionDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceTransActionDAction.
    def enterReplaceTransActionDAction(self, ctx:DParser.ReplaceTransActionDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceTransActionDAction.
    def exitReplaceTransActionDAction(self, ctx:DParser.ReplaceTransActionDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceTransTriggerDAction.
    def enterReplaceTransTriggerDAction(self, ctx:DParser.ReplaceTransTriggerDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceTransTriggerDAction.
    def exitReplaceTransTriggerDAction(self, ctx:DParser.ReplaceTransTriggerDActionContext):
        pass


    # Enter a parse tree produced by DParser#alterTransDAction.
    def enterAlterTransDAction(self, ctx:DParser.AlterTransDActionContext):
        pass

    # Exit a parse tree produced by DParser#alterTransDAction.
    def exitAlterTransDAction(self, ctx:DParser.AlterTransDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceDAction.
    def enterReplaceDAction(self, ctx:DParser.ReplaceDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceDAction.
    def exitReplaceDAction(self, ctx:DParser.ReplaceDActionContext):
        pass


    # Enter a parse tree produced by DParser#setWeightDAction.
    def enterSetWeightDAction(self, ctx:DParser.SetWeightDActionContext):
        pass

    # Exit a parse tree produced by DParser#setWeightDAction.
    def exitSetWeightDAction(self, ctx:DParser.SetWeightDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceSayDAction.
    def enterReplaceSayDAction(self, ctx:DParser.ReplaceSayDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceSayDAction.
    def exitReplaceSayDAction(self, ctx:DParser.ReplaceSayDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceStateTriggerDAction.
    def enterReplaceStateTriggerDAction(self, ctx:DParser.ReplaceStateTriggerDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceStateTriggerDAction.
    def exitReplaceStateTriggerDAction(self, ctx:DParser.ReplaceStateTriggerDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceTriggerTextDAction.
    def enterReplaceTriggerTextDAction(self, ctx:DParser.ReplaceTriggerTextDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceTriggerTextDAction.
    def exitReplaceTriggerTextDAction(self, ctx:DParser.ReplaceTriggerTextDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceTriggerTextRegexpDAction.
    def enterReplaceTriggerTextRegexpDAction(self, ctx:DParser.ReplaceTriggerTextRegexpDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceTriggerTextRegexpDAction.
    def exitReplaceTriggerTextRegexpDAction(self, ctx:DParser.ReplaceTriggerTextRegexpDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceActionTextDAction.
    def enterReplaceActionTextDAction(self, ctx:DParser.ReplaceActionTextDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceActionTextDAction.
    def exitReplaceActionTextDAction(self, ctx:DParser.ReplaceActionTextDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceActionTextRegexpDAction.
    def enterReplaceActionTextRegexpDAction(self, ctx:DParser.ReplaceActionTextRegexpDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceActionTextRegexpDAction.
    def exitReplaceActionTextRegexpDAction(self, ctx:DParser.ReplaceActionTextRegexpDActionContext):
        pass


    # Enter a parse tree produced by DParser#replaceActionTextProcessDAction.
    def enterReplaceActionTextProcessDAction(self, ctx:DParser.ReplaceActionTextProcessDActionContext):
        pass

    # Exit a parse tree produced by DParser#replaceActionTextProcessDAction.
    def exitReplaceActionTextProcessDAction(self, ctx:DParser.ReplaceActionTextProcessDActionContext):
        pass


    # Enter a parse tree produced by DParser#ReplaceActionTextProcessRegexpDAction.
    def enterReplaceActionTextProcessRegexpDAction(self, ctx:DParser.ReplaceActionTextProcessRegexpDActionContext):
        pass

    # Exit a parse tree produced by DParser#ReplaceActionTextProcessRegexpDAction.
    def exitReplaceActionTextProcessRegexpDAction(self, ctx:DParser.ReplaceActionTextProcessRegexpDActionContext):
        pass


    # Enter a parse tree produced by DParser#alterTransCommand.
    def enterAlterTransCommand(self, ctx:DParser.AlterTransCommandContext):
        pass

    # Exit a parse tree produced by DParser#alterTransCommand.
    def exitAlterTransCommand(self, ctx:DParser.AlterTransCommandContext):
        pass


    # Enter a parse tree produced by DParser#conditionRule.
    def enterConditionRule(self, ctx:DParser.ConditionRuleContext):
        pass

    # Exit a parse tree produced by DParser#conditionRule.
    def exitConditionRule(self, ctx:DParser.ConditionRuleContext):
        pass


    # Enter a parse tree produced by DParser#ifThenState.
    def enterIfThenState(self, ctx:DParser.IfThenStateContext):
        pass

    # Exit a parse tree produced by DParser#ifThenState.
    def exitIfThenState(self, ctx:DParser.IfThenStateContext):
        pass


    # Enter a parse tree produced by DParser#appendiState.
    def enterAppendiState(self, ctx:DParser.AppendiStateContext):
        pass

    # Exit a parse tree produced by DParser#appendiState.
    def exitAppendiState(self, ctx:DParser.AppendiStateContext):
        pass


    # Enter a parse tree produced by DParser#chain2State.
    def enterChain2State(self, ctx:DParser.Chain2StateContext):
        pass

    # Exit a parse tree produced by DParser#chain2State.
    def exitChain2State(self, ctx:DParser.Chain2StateContext):
        pass


    # Enter a parse tree produced by DParser#chain2DlgRule.
    def enterChain2DlgRule(self, ctx:DParser.Chain2DlgRuleContext):
        pass

    # Exit a parse tree produced by DParser#chain2DlgRule.
    def exitChain2DlgRule(self, ctx:DParser.Chain2DlgRuleContext):
        pass


    # Enter a parse tree produced by DParser#chain2ElementRule.
    def enterChain2ElementRule(self, ctx:DParser.Chain2ElementRuleContext):
        pass

    # Exit a parse tree produced by DParser#chain2ElementRule.
    def exitChain2ElementRule(self, ctx:DParser.Chain2ElementRuleContext):
        pass


    # Enter a parse tree produced by DParser#ifThenTransition.
    def enterIfThenTransition(self, ctx:DParser.IfThenTransitionContext):
        pass

    # Exit a parse tree produced by DParser#ifThenTransition.
    def exitIfThenTransition(self, ctx:DParser.IfThenTransitionContext):
        pass


    # Enter a parse tree produced by DParser#replyTransition.
    def enterReplyTransition(self, ctx:DParser.ReplyTransitionContext):
        pass

    # Exit a parse tree produced by DParser#replyTransition.
    def exitReplyTransition(self, ctx:DParser.ReplyTransitionContext):
        pass


    # Enter a parse tree produced by DParser#copyTransTransition.
    def enterCopyTransTransition(self, ctx:DParser.CopyTransTransitionContext):
        pass

    # Exit a parse tree produced by DParser#copyTransTransition.
    def exitCopyTransTransition(self, ctx:DParser.CopyTransTransitionContext):
        pass


    # Enter a parse tree produced by DParser#copyTransLateTransition.
    def enterCopyTransLateTransition(self, ctx:DParser.CopyTransLateTransitionContext):
        pass

    # Exit a parse tree produced by DParser#copyTransLateTransition.
    def exitCopyTransLateTransition(self, ctx:DParser.CopyTransLateTransitionContext):
        pass


    # Enter a parse tree produced by DParser#gotoTransitionTarget.
    def enterGotoTransitionTarget(self, ctx:DParser.GotoTransitionTargetContext):
        pass

    # Exit a parse tree produced by DParser#gotoTransitionTarget.
    def exitGotoTransitionTarget(self, ctx:DParser.GotoTransitionTargetContext):
        pass


    # Enter a parse tree produced by DParser#externTransitionTarget.
    def enterExternTransitionTarget(self, ctx:DParser.ExternTransitionTargetContext):
        pass

    # Exit a parse tree produced by DParser#externTransitionTarget.
    def exitExternTransitionTarget(self, ctx:DParser.ExternTransitionTargetContext):
        pass


    # Enter a parse tree produced by DParser#exitTransitionTarget.
    def enterExitTransitionTarget(self, ctx:DParser.ExitTransitionTargetContext):
        pass

    # Exit a parse tree produced by DParser#exitTransitionTarget.
    def exitExitTransitionTarget(self, ctx:DParser.ExitTransitionTargetContext):
        pass


    # Enter a parse tree produced by DParser#endChainActionEpilog.
    def enterEndChainActionEpilog(self, ctx:DParser.EndChainActionEpilogContext):
        pass

    # Exit a parse tree produced by DParser#endChainActionEpilog.
    def exitEndChainActionEpilog(self, ctx:DParser.EndChainActionEpilogContext):
        pass


    # Enter a parse tree produced by DParser#externChainActionEpilog.
    def enterExternChainActionEpilog(self, ctx:DParser.ExternChainActionEpilogContext):
        pass

    # Exit a parse tree produced by DParser#externChainActionEpilog.
    def exitExternChainActionEpilog(self, ctx:DParser.ExternChainActionEpilogContext):
        pass


    # Enter a parse tree produced by DParser#copyTransChainActionEpilog.
    def enterCopyTransChainActionEpilog(self, ctx:DParser.CopyTransChainActionEpilogContext):
        pass

    # Exit a parse tree produced by DParser#copyTransChainActionEpilog.
    def exitCopyTransChainActionEpilog(self, ctx:DParser.CopyTransChainActionEpilogContext):
        pass


    # Enter a parse tree produced by DParser#copyTransLateChainActionEpilog.
    def enterCopyTransLateChainActionEpilog(self, ctx:DParser.CopyTransLateChainActionEpilogContext):
        pass

    # Exit a parse tree produced by DParser#copyTransLateChainActionEpilog.
    def exitCopyTransLateChainActionEpilog(self, ctx:DParser.CopyTransLateChainActionEpilogContext):
        pass


    # Enter a parse tree produced by DParser#exitChainActionEpilog.
    def enterExitChainActionEpilog(self, ctx:DParser.ExitChainActionEpilogContext):
        pass

    # Exit a parse tree produced by DParser#exitChainActionEpilog.
    def exitExitChainActionEpilog(self, ctx:DParser.ExitChainActionEpilogContext):
        pass


    # Enter a parse tree produced by DParser#endWithTransitionsChainActionEpilog.
    def enterEndWithTransitionsChainActionEpilog(self, ctx:DParser.EndWithTransitionsChainActionEpilogContext):
        pass

    # Exit a parse tree produced by DParser#endWithTransitionsChainActionEpilog.
    def exitEndWithTransitionsChainActionEpilog(self, ctx:DParser.EndWithTransitionsChainActionEpilogContext):
        pass


    # Enter a parse tree produced by DParser#replyTransitionFeature.
    def enterReplyTransitionFeature(self, ctx:DParser.ReplyTransitionFeatureContext):
        pass

    # Exit a parse tree produced by DParser#replyTransitionFeature.
    def exitReplyTransitionFeature(self, ctx:DParser.ReplyTransitionFeatureContext):
        pass


    # Enter a parse tree produced by DParser#doTransitionFeature.
    def enterDoTransitionFeature(self, ctx:DParser.DoTransitionFeatureContext):
        pass

    # Exit a parse tree produced by DParser#doTransitionFeature.
    def exitDoTransitionFeature(self, ctx:DParser.DoTransitionFeatureContext):
        pass


    # Enter a parse tree produced by DParser#journalTransitionFeature.
    def enterJournalTransitionFeature(self, ctx:DParser.JournalTransitionFeatureContext):
        pass

    # Exit a parse tree produced by DParser#journalTransitionFeature.
    def exitJournalTransitionFeature(self, ctx:DParser.JournalTransitionFeatureContext):
        pass


    # Enter a parse tree produced by DParser#solvedJournalTransitionFeature.
    def enterSolvedJournalTransitionFeature(self, ctx:DParser.SolvedJournalTransitionFeatureContext):
        pass

    # Exit a parse tree produced by DParser#solvedJournalTransitionFeature.
    def exitSolvedJournalTransitionFeature(self, ctx:DParser.SolvedJournalTransitionFeatureContext):
        pass


    # Enter a parse tree produced by DParser#unsolvedJournalTransitionFeature.
    def enterUnsolvedJournalTransitionFeature(self, ctx:DParser.UnsolvedJournalTransitionFeatureContext):
        pass

    # Exit a parse tree produced by DParser#unsolvedJournalTransitionFeature.
    def exitUnsolvedJournalTransitionFeature(self, ctx:DParser.UnsolvedJournalTransitionFeatureContext):
        pass


    # Enter a parse tree produced by DParser#flagsTransitionFeature.
    def enterFlagsTransitionFeature(self, ctx:DParser.FlagsTransitionFeatureContext):
        pass

    # Exit a parse tree produced by DParser#flagsTransitionFeature.
    def exitFlagsTransitionFeature(self, ctx:DParser.FlagsTransitionFeatureContext):
        pass


    # Enter a parse tree produced by DParser#chainDlgRule.
    def enterChainDlgRule(self, ctx:DParser.ChainDlgRuleContext):
        pass

    # Exit a parse tree produced by DParser#chainDlgRule.
    def exitChainDlgRule(self, ctx:DParser.ChainDlgRuleContext):
        pass


    # Enter a parse tree produced by DParser#monologChainBlock.
    def enterMonologChainBlock(self, ctx:DParser.MonologChainBlockContext):
        pass

    # Exit a parse tree produced by DParser#monologChainBlock.
    def exitMonologChainBlock(self, ctx:DParser.MonologChainBlockContext):
        pass


    # Enter a parse tree produced by DParser#branchChainBlock.
    def enterBranchChainBlock(self, ctx:DParser.BranchChainBlockContext):
        pass

    # Exit a parse tree produced by DParser#branchChainBlock.
    def exitBranchChainBlock(self, ctx:DParser.BranchChainBlockContext):
        pass


    # Enter a parse tree produced by DParser#chainElementRule.
    def enterChainElementRule(self, ctx:DParser.ChainElementRuleContext):
        pass

    # Exit a parse tree produced by DParser#chainElementRule.
    def exitChainElementRule(self, ctx:DParser.ChainElementRuleContext):
        pass


    # Enter a parse tree produced by DParser#fileRule.
    def enterFileRule(self, ctx:DParser.FileRuleContext):
        pass

    # Exit a parse tree produced by DParser#fileRule.
    def exitFileRule(self, ctx:DParser.FileRuleContext):
        pass


    # Enter a parse tree produced by DParser#sayTextRule.
    def enterSayTextRule(self, ctx:DParser.SayTextRuleContext):
        pass

    # Exit a parse tree produced by DParser#sayTextRule.
    def exitSayTextRule(self, ctx:DParser.SayTextRuleContext):
        pass


    # Enter a parse tree produced by DParser#traLineRule.
    def enterTraLineRule(self, ctx:DParser.TraLineRuleContext):
        pass

    # Exit a parse tree produced by DParser#traLineRule.
    def exitTraLineRule(self, ctx:DParser.TraLineRuleContext):
        pass


    # Enter a parse tree produced by DParser#genderedText.
    def enterGenderedText(self, ctx:DParser.GenderedTextContext):
        pass

    # Exit a parse tree produced by DParser#genderedText.
    def exitGenderedText(self, ctx:DParser.GenderedTextContext):
        pass


    # Enter a parse tree produced by DParser#genderNeutralText.
    def enterGenderNeutralText(self, ctx:DParser.GenderNeutralTextContext):
        pass

    # Exit a parse tree produced by DParser#genderNeutralText.
    def exitGenderNeutralText(self, ctx:DParser.GenderNeutralTextContext):
        pass


    # Enter a parse tree produced by DParser#referencedText.
    def enterReferencedText(self, ctx:DParser.ReferencedTextContext):
        pass

    # Exit a parse tree produced by DParser#referencedText.
    def exitReferencedText(self, ctx:DParser.ReferencedTextContext):
        pass


    # Enter a parse tree produced by DParser#stringRule.
    def enterStringRule(self, ctx:DParser.StringRuleContext):
        pass

    # Exit a parse tree produced by DParser#stringRule.
    def exitStringRule(self, ctx:DParser.StringRuleContext):
        pass


    # Enter a parse tree produced by DParser#stringLiteralRule.
    def enterStringLiteralRule(self, ctx:DParser.StringLiteralRuleContext):
        pass

    # Exit a parse tree produced by DParser#stringLiteralRule.
    def exitStringLiteralRule(self, ctx:DParser.StringLiteralRuleContext):
        pass


    # Enter a parse tree produced by DParser#identifierRule.
    def enterIdentifierRule(self, ctx:DParser.IdentifierRuleContext):
        pass

    # Exit a parse tree produced by DParser#identifierRule.
    def exitIdentifierRule(self, ctx:DParser.IdentifierRuleContext):
        pass


    # Enter a parse tree produced by DParser#referenceRule.
    def enterReferenceRule(self, ctx:DParser.ReferenceRuleContext):
        pass

    # Exit a parse tree produced by DParser#referenceRule.
    def exitReferenceRule(self, ctx:DParser.ReferenceRuleContext):
        pass


    # Enter a parse tree produced by DParser#sharpNumberRule.
    def enterSharpNumberRule(self, ctx:DParser.SharpNumberRuleContext):
        pass

    # Exit a parse tree produced by DParser#sharpNumberRule.
    def exitSharpNumberRule(self, ctx:DParser.SharpNumberRuleContext):
        pass


    # Enter a parse tree produced by DParser#soundRule.
    def enterSoundRule(self, ctx:DParser.SoundRuleContext):
        pass

    # Exit a parse tree produced by DParser#soundRule.
    def exitSoundRule(self, ctx:DParser.SoundRuleContext):
        pass



del DParser