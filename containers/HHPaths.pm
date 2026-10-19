# Container-specific HHPaths.pm for DPAM v2.0
# Configured for Apptainer container with conda-installed hhsuite and psipred
# All paths point to /opt/conda/envs/dpam (the conda environment prefix)

package HHPaths;

use vars qw(@ISA @EXPORT @EXPORT_OK %EXPORT_TAGS $VERSION);
use Exporter;
our $v;
our $VERSION = "version 3.0.0 (15-03-2015)";
our @ISA     = qw(Exporter);
our @EXPORT  = qw($VERSION $hhlib $hhdata $hhbin $hhscripts $execdir $datadir $ncbidir $dummydb $pdbdir $dsspdir $dssp $cs_lib $context_lib $v);
push @EXPORT, qw($hhshare $hhbdata);

# Conda environment prefix inside the container
my $conda_prefix = "/opt/conda/envs/dpam";

# PSIPRED paths (installed via bioconda into conda env)
our $execdir = "$conda_prefix/bin";
our $datadir = "$conda_prefix/share/psipred/data";
our $ncbidir = "$conda_prefix/bin";

# PDB/DSSP paths (not used for addss.pl SS prediction mode)
our $pdbdir  = "/dev/null";
our $dsspdir = "/dev/null";
our $dssp    = "/dev/null";

# HH-suite paths (installed via bioconda into conda env)
# Bioconda installs data/ and scripts/ directly under $CONDA_PREFIX
my $hhsuite_system = $conda_prefix;
our $hhlib    = $hhsuite_system;
our $hhshare  = $hhsuite_system;
our $hhdata   = $hhsuite_system."/data";
our $hhbdata  = $hhsuite_system."/data";
our $hhbin    = "$conda_prefix/bin";
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
