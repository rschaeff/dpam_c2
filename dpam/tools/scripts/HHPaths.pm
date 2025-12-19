# Custom HHPaths.pm for DPAM v2.0
# Configured to use conda environment paths for PSIPRED and BLAST

package HHPaths;

use vars qw(@ISA @EXPORT @EXPORT_OK %EXPORT_TAGS $VERSION);
use Exporter;
our $v;
our $VERSION = "version 3.0.0 (15-03-2015)";
our @ISA     = qw(Exporter);
our @EXPORT  = qw($VERSION $hhlib $hhdata $hhbin $hhscripts $execdir $datadir $ncbidir $dummydb $pdbdir $dsspdir $dssp $cs_lib $context_lib $v);
push @EXPORT, qw($hhshare $hhbdata);

# Get paths from conda environment
my $conda_prefix = $ENV{"CONDA_PREFIX"} || die "CONDA_PREFIX not set";

# PSIPRED paths (from conda)
our $execdir = "$conda_prefix/bin";                      # psipred, psipass2 binaries
our $datadir = "$conda_prefix/share/psipred/data";       # psipred weight files
our $ncbidir = "$conda_prefix/bin";                      # blastpgp, makemat, formatdb

# PDB/DSSP paths (not used for addss.pl SS prediction mode)
our $pdbdir  = "/dev/null";
our $dsspdir = "/dev/null";
our $dssp    = "/dev/null";

# HH-suite paths (use system hhsuite for data/binaries)
# HHLIB may point to DPAM's tools dir, so use explicit system path for hhsuite
my $hhsuite_system = "/sw/apps/hh-suite";
our $hhlib    = $hhsuite_system;
our $hhshare  = $hhsuite_system;
our $hhdata   = $hhsuite_system."/data";
our $hhbdata  = $hhsuite_system."/data";
our $hhbin    = $hhsuite_system."/bin";
our $hhscripts= $hhsuite_system."/scripts";
our $dummydb  = $hhsuite_system."/data/do_not_delete";

# HHblits data files
our $cs_lib = "$hhdata/cs219.lib";
our $context_lib = "$hhdata/context_data.lib";

# Add hh-suite scripts directory to search path
$ENV{"PATH"} = $hhscripts.":".$ENV{"PATH"};

################################################################################################
### System command with return value parsed from output
################################################################################################
sub System()
{
    if ($v>=2) {printf(STDERR "\$ %s\n",$_[0]);}
    system($_[0]);
    if ($? == -1) {
        die("\nError: failed to execute '$_[0]': $!\n\n");
    } elsif ($? != 0) {
        printf(STDERR "\nError: command '$_[0]' returned error code %d\n\n", $? >> 8);
        return 1;
   }
    return $?;
}

return 1;
